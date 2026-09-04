"""
Persistent history of finished reports, one JSON file on disk
(config.REPORTS_FILE). This is separate from the per-query Chroma DB and
PDF store - those get wiped at the start of every new query, but this file
lives directly under data/ (not inside chroma_db/ or pdfs/) so it survives
both query resets and server restarts. Every report the Report Agent
produces gets appended here; nothing is ever overwritten or auto-deleted -
only an explicit DELETE /reports clears it.
"""
import json
import logging
import os
import time

from config import REPORTS_FILE, DATA_DIR

logger = logging.getLogger("report_store")


def _load() -> list:
    if not os.path.exists(REPORTS_FILE):
        return []
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read report history (%s) - starting fresh", e)
        return []


def _save(records: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_report(run_id: str, topic: str, question: str, report_text: str) -> dict:
    """Appends a finished report to the history file and returns the saved record."""
    record = {
        "run_id": run_id,
        "topic": topic,
        "question": question,
        "report": report_text,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    records = _load()
    records.append(record)
    _save(records)
    logger.info("Report history: saved report for run_id=%s (total stored: %d)", run_id, len(records))
    return record


def list_reports() -> list:
    """Lightweight listing (no full report text) for browsing history."""
    records = _load()
    return [
        {"run_id": r["run_id"], "topic": r["topic"], "question": r.get("question", ""), "saved_at": r["saved_at"]}
        for r in records
    ]


def get_report(run_id: str) -> dict | None:
    """Full stored record (including report text) for one run_id, or None."""
    for r in _load():
        if r["run_id"] == run_id:
            return r
    return None


def clear_reports():
    _save([])
    logger.info("Report history: cleared")
