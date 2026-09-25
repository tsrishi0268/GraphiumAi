"""
main.py
FastAPI app for the Memory Agent.

Run with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

import store
import ingestion
import retrieval
import llm
import agent

app = FastAPI(title="Memory Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store.init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ---------------------------------------------------------------- ingestion

@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), source_type: str = Form(None)):
    raw = await file.read()
    text = ingestion.parse_file(file.filename, raw)
    stype = ingestion.detect_source_type(file.filename, source_type)

    chunks = ingestion.chunk_text(text)
    for c in chunks:
        entities = ingestion.extract_entities(c)
        doc_date = ingestion.guess_date(c)
        store.add_chunk(c, stype, file.filename, doc_date, entities)

    return {"filename": file.filename, "source_type": stype, "chunks_added": len(chunks)}


class TextIngest(BaseModel):
    text: str
    source_type: str = "note"
    source_name: str = "manual entry"


@app.post("/api/ingest/text")
def ingest_text(body: TextIngest):
    chunks = ingestion.chunk_text(body.text)
    for c in chunks:
        entities = ingestion.extract_entities(c)
        doc_date = ingestion.guess_date(c)
        store.add_chunk(c, body.source_type, body.source_name, doc_date, entities)
    return {"chunks_added": len(chunks)}


# ------------------------------------------------------------------- query

class Query(BaseModel):
    question: str


@app.post("/api/query")
def query(body: Query):
    chunks = retrieval.search(body.question, top_k=6)
    text, action = llm.answer(body.question, chunks)

    executed_action = agent.execute_action(action) if action else None

    return {
        "answer": text,
        "sources": [
            {
                "source_type": c["source_type"],
                "source_name": c["source_name"],
                "doc_date": c["doc_date"],
                "snippet": c["text"][:300],
                "score": round(c["score"], 3),
            }
            for c in chunks
        ],
        "action": executed_action,
    }


# ------------------------------------------------------------------- misc

@app.get("/api/memory")
def memory():
    return store.all_chunks()


@app.get("/api/actions")
def actions():
    return store.all_actions()


@app.post("/api/reset")
def reset():
    store.clear_all()
    return {"status": "cleared"}
