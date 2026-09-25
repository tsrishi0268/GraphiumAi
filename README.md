# Memory Agent

A personal, searchable memory built from your WhatsApp exports, emails, PDFs,
notes, screenshots and calendar — with source-cited, conflict-aware answers
and an optional autonomous action step.

## How it maps to the challenge

| Requirement | How it's handled |
|---|---|
| Retrieve across data types | `ingestion.py` parses `.txt/.md` (notes/WhatsApp), `.eml` (email), `.pdf`, `.ics/.csv` (calendar), `.png/.jpg` (screenshots via OCR) into a common chunk format |
| Context & relationships | Each chunk stores lightweight extracted entities + dates (`ingestion.extract_entities`); the LLM prompt is given all retrieved chunks together so it can connect people/events/docs |
| Conflicting information | The system prompt explicitly instructs the model to flag contradictions between numbered sources under a "Conflicting information" note |
| Source references | Every answer is grounded in numbered `[1] [2]` sources, and the UI shows the source type/filename/date under each answer |
| Avoid inventing info | The prompt restricts the model to only the retrieved sources, and it must say when it doesn't know — retrieval score is also surfaced |
| Bonus: autonomous action | The model can emit a fenced `action` JSON block (reminder / draft email / calendar event); `agent.py` executes it into an "Actions taken" outbox shown in the sidebar |

## Setup (in VS Code)

1. Open this folder in VS Code.
2. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. (Optional, for real LLM answers instead of the extractive fallback) Copy
   `.env.example` to `.env` and add an `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.
   Without a key the app still runs and returns cited excerpts, just not a
   synthesized answer.
4. Run the server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
5. Open **http://localhost:8000** in your browser.

> Screenshot OCR needs the `tesseract` binary installed separately
> (`brew install tesseract` / `apt install tesseract-ocr`). If it's missing,
> screenshot ingestion just returns a friendly warning instead of crashing.

## Demo script for judges

1. Upload `sample_data/whatsapp_export.txt`, `sample_data/email.eml`, and
   `sample_data/schedule.ics` (included).
2. Ask: **"When and where am I meeting Raj?"** → shows a cited, synthesized
   answer pulling from both the WhatsApp chat and the calendar.
3. Ask something that appears differently in two sources (see the sample
   data's deliberate time conflict) → the agent flags the conflict instead of
   picking one silently.
4. Ask something not in the data (e.g. "What's my blood type?") → the agent
   says it doesn't know, instead of guessing.
5. Ask: **"Remind me to confirm the venue with Raj"** → the agent creates an
   action, visible in the "Actions taken" sidebar — the autonomous bonus.

## Project structure

```
memory-agent/
  backend/
    main.py          FastAPI app + routes
    ingestion.py      File parsers (pdf/txt/ics/csv/images) + chunking
    retrieval.py       TF-IDF retrieval
    llm.py               Grounded answer generation (Anthropic/OpenAI/fallback)
    agent.py            Executes bonus autonomous actions
    store.py            SQLite storage
  frontend/
    index.html / app.js / style.css   Single-page chat + upload UI
  sample_data/         Ready-made files for your demo
```

## Ideas if you have extra time

- Swap TF-IDF for real embeddings (OpenAI `text-embedding-3-small` or local
  `sentence-transformers`) for better semantic recall.
- Use spaCy for real named-entity extraction and build a people/events graph
  view.
- Wire `agent.py`'s actions to real Google Calendar / Gmail APIs.
- Add a timeline view grouping chunks by `doc_date`.
