"""
Persistent history for the "Ask about this research" chatbot.

Same pattern as report_store.py: one JSON file living directly under
DATA_DIR (config.CHAT_HISTORY_FILE), so it survives both the per-query
Chroma/PDF reset (db_manager.py only wipes chroma_db/ and pdfs/) and
server restarts. Every question/answer exchange is appended here; nothing
is ever overwritten or auto-deleted - only an explicit DELETE clears it.
"""
import json
import logging
import os
import time

from config import CHAT_HISTORY_FILE, DATA_DIR

logger = logging.getLogger("chat_store")


def _load() -> list:
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    try:
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read chat history (%s) - starting fresh", e)
        return []


def _save(records: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_message(run_id: str, question: str, answer: str) -> dict:
    """Appends one question/answer exchange to the history file and returns it."""
    record = {
        "run_id": run_id,
        "question": question,
        "answer": answer,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    records = _load()
    records.append(record)
    _save(records)
    logger.info("Chat history: saved exchange for run_id=%s (total stored: %d)", run_id, len(records))
    return record


def get_history(run_id: str) -> list:
    """All saved exchanges for one run_id, in the order they were asked."""
    return [r for r in _load() if r["run_id"] == run_id]


def clear_history(run_id: str | None = None):
    """Clears chat history for one run_id, or everything if run_id is None."""
    if run_id is None:
        _save([])
        logger.info("Chat history: cleared all")
        return
    records = [r for r in _load() if r["run_id"] != run_id]
    _save(records)
    logger.info("Chat history: cleared run_id=%s", run_id)
