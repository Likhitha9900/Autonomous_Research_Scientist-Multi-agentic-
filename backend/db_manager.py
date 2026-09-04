"""
Enforces "fresh database per query":
- reset_for_new_query(): wipes Chroma DB + PDF folder, recreates them empty.
  Called by the Supervisor node at the start of every /research call.
- clear_pdfs(): wipes just the PDF folder. Called after each PDF is used by
  the Literature Agent, and again as a safety net once a run finishes.
- clear_all(): full wipe, used by the manual /reset endpoint.
"""
import os
import shutil
import logging

from config import PDF_DIR, CHROMA_DIR, DATA_DIR

logger = logging.getLogger("db_manager")


def _fresh_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def reset_for_new_query():
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info("Resetting Chroma DB at %s", CHROMA_DIR)
    _fresh_dir(CHROMA_DIR)
    logger.info("Resetting PDF store at %s", PDF_DIR)
    _fresh_dir(PDF_DIR)


def clear_pdfs():
    if os.path.exists(PDF_DIR):
        shutil.rmtree(PDF_DIR)
    os.makedirs(PDF_DIR, exist_ok=True)
    logger.info("Cleared PDF store at %s", PDF_DIR)


def clear_all():
    _fresh_dir(CHROMA_DIR)
    _fresh_dir(PDF_DIR)
