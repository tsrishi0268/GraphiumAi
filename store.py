"""
store.py
Simple SQLite-backed store for memory chunks + a mock "actions" table
for the bonus autonomous agent (reminders, drafted emails, etc.)
"""
import sqlite3
import json
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "memory.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source_type TEXT NOT NULL,   -- whatsapp, email, pdf, note, calendar, screenshot
            source_name TEXT NOT NULL,   -- original filename
            doc_date TEXT,               -- best-guess date associated with the chunk
            entities TEXT,                -- JSON list of extracted names/keywords
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,   -- reminder, draft_email, calendar_event
            payload TEXT NOT NULL,       -- JSON
            status TEXT NOT NULL,        -- pending, done
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_chunk(text, source_type, source_name, doc_date, entities):
    conn = get_conn()
    conn.execute(
        "INSERT INTO chunks (text, source_type, source_name, doc_date, entities, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (text, source_type, source_name, doc_date, json.dumps(entities), time.time()),
    )
    conn.commit()
    conn.close()


def all_chunks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chunks ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_action(action_type, payload):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO actions (action_type, payload, status, created_at) VALUES (?, ?, 'pending', ?)",
        (action_type, json.dumps(payload), time.time()),
    )
    conn.commit()
    action_id = cur.lastrowid
    conn.close()
    return action_id


def all_actions():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM actions ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_all():
    conn = get_conn()
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM actions")
    conn.commit()
    conn.close()
