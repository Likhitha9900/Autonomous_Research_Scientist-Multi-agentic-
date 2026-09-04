"""
Central configuration for the Autonomous Research Scientist backend.
All storage paths are wiped and recreated fresh at the start of every new
query (see db_manager.py) so nothing leaks between queries.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_TEMPERATURE = 0.2

# --- Embeddings ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --- Storage paths (wiped per query) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_DIR = os.path.join(DATA_DIR, "pdfs")          # cleared after every query
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")  # deleted + recreated per query

# --- Literature search ---
# How many papers the Literature Agent pulls per query. Raise this in your
# .env file (MAX_PAPERS=100) for broader coverage - just be aware every
# extra paper here also means one extra Groq call in the Analysis Agent,
# so larger values are slower and use more of your Groq quota.
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "50"))
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# --- RAG Retrieve Agent (runs after Literature, before Analysis) ---
# How many of the found papers actually get passed on to the (expensive,
# one-LLM-call-per-paper) Analysis Agent. Lower = fewer Groq calls, less
# rate-limit risk, faster runs; higher = broader coverage.
TOP_K_RELEVANT_PAPERS = int(os.getenv("TOP_K_RELEVANT_PAPERS", "15"))
# How many raw chunks to pull back when ranking papers by relevance - kept
# wide so we see enough distinct papers before collapsing to unique paper_ids.
CHUNK_SEARCH_K = int(os.getenv("CHUNK_SEARCH_K", "60"))

# --- Chroma collection names (fixed - the whole DB folder is wiped per query) ---
COLLECTION_PAPERS = "papers_v1"
COLLECTION_ANALYSIS = "paper_analysis_v1"

# --- Report history (persists across queries and server restarts) ---
# Lives directly under DATA_DIR, NOT inside chroma_db/ or pdfs/, so it is
# untouched by db_manager's per-query reset - every finished report stays
# here until you explicitly clear it via DELETE /reports.
REPORTS_FILE = os.path.join(DATA_DIR, "reports_history.json")

# --- Chat Agent (ask-anything retriever over a run's collected data) ---
# How many chunks to pull back per Chroma collection (papers + analyses)
# when answering a chat question. Kept small since both sets of hits get
# combined into one prompt alongside the run's structured findings, and
# small Groq models (e.g. openai/gpt-oss-20b) cap requests at 8000 tokens
# per minute - an oversized prompt gets rejected outright (HTTP 413)
# before it even reaches the model.
CHAT_TOP_K_CHUNKS = int(os.getenv("CHAT_TOP_K_CHUNKS", "3"))
# Hard per-chunk / per-list-item / per-report character caps so one huge
# paper excerpt, a long list of gaps, or a lengthy final report can't blow
# the whole prompt past the model's token limit on their own.
CHAT_CHUNK_CHAR_LIMIT = int(os.getenv("CHAT_CHUNK_CHAR_LIMIT", "500"))
CHAT_LIST_ITEM_CHAR_LIMIT = int(os.getenv("CHAT_LIST_ITEM_CHAR_LIMIT", "220"))
CHAT_MAX_LIST_ITEMS = int(os.getenv("CHAT_MAX_LIST_ITEMS", "8"))
CHAT_REPORT_CHAR_LIMIT = int(os.getenv("CHAT_REPORT_CHAR_LIMIT", "1500"))
# Same persistence pattern as REPORTS_FILE - lives directly under DATA_DIR
# so per-query resets never touch it; only DELETE /chat/{run_id} or
# DELETE /chat clears it.
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
