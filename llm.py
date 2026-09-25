"""
llm.py
Wraps whichever LLM API key is available (Anthropic or OpenAI) to turn
retrieved chunks into a grounded, cited answer. Falls back to a plain
extractive summary (no external call) if no key is set, so the app still
runs for free/offline.

The system prompt is the core of "avoid confidently inventing information":
the model is told to answer ONLY from the provided sources, to say when it
doesn't know, to flag contradictions between sources, and to cite [n] for
every claim.
"""
import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are the Memory Agent, a personal assistant that answers questions \
ONLY using the numbered source excerpts the user provides below. These come from the \
user's own WhatsApp chats, emails, PDFs, notes, screenshots and calendar.

Rules you must follow:
1. Only state facts that are directly supported by the numbered sources. Never invent \
   names, dates, or details that are not present in the sources.
2. Every factual claim in your answer must end with a citation like [1] or [2,3] \
   referring to the source numbers used.
3. If the sources disagree with each other (e.g. two different times for the same \
   event, or conflicting facts), explicitly say so under a "Conflicting information" \
   note, and cite both sources.
4. If the sources don't contain enough information to answer, say clearly that you \
   don't have that information in the user's memory yet. Do not guess.
5. If the user's request implies taking an action (e.g. "remind me", "draft an email", \
   "add this to my calendar"), after your answer output a fenced block:
   ```action
   {"type": "reminder" | "draft_email" | "calendar_event", "payload": {...}}
   ```
   Only do this if the user clearly asked for an action, and base the payload only on \
   retrieved facts.

Be concise. Do not restate the sources verbatim; synthesize them.
"""


def _format_sources(chunks):
    lines = []
    for i, c in enumerate(chunks, start=1):
        date = c.get("doc_date") or "unknown date"
        lines.append(
            f"[{i}] (source: {c['source_type']} - {c['source_name']}, {date})\n{c['text']}"
        )
    return "\n\n".join(lines)


def _extractive_fallback(query, chunks):
    """No API key available: just surface the top matching chunks with citations
    instead of a synthesized answer."""
    if not chunks:
        return "I don't have any information about that in your memory yet.", []
    lines = ["I don't have an LLM key configured, so here are the most relevant "
             "things I found in your memory (set ANTHROPIC_API_KEY or OPENAI_API_KEY "
             "in backend/.env for a synthesized, conflict-aware answer):\n"]
    for i, c in enumerate(chunks, start=1):
        date = c.get("doc_date") or "unknown date"
        snippet = c["text"][:280].replace("\n", " ")
        lines.append(f"[{i}] ({c['source_type']} - {c['source_name']}, {date}): {snippet}")
    return "\n".join(lines), []


def _call_anthropic(query, chunks):
    sources = _format_sources(chunks)
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 800,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": f"Sources:\n{sources}\n\nQuestion: {query}"}
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return text


def _call_openai(query, chunks):
    sources = _format_sources(chunks)
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "content-type": "application/json"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Sources:\n{sources}\n\nQuestion: {query}"},
            ],
            "max_tokens": 800,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _extract_action(text):
    m = re.search(r"```action\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not m:
        return text, None
    clean_text = text[: m.start()].strip()
    try:
        action = json.loads(m.group(1))
    except json.JSONDecodeError:
        action = None
    return clean_text, action


def answer(query, chunks):
    """Returns (answer_text, action_dict_or_None)."""
    if not chunks:
        return "I don't have any information about that in your memory yet.", None

    if ANTHROPIC_KEY:
        raw = _call_anthropic(query, chunks)
    elif OPENAI_KEY:
        raw = _call_openai(query, chunks)
    else:
        text, _ = _extractive_fallback(query, chunks)
        return text, None

    text, action = _extract_action(raw)
    return text, action
