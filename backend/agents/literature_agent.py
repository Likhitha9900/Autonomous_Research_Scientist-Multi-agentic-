"""
Agent 1 - Literature Research Agent
Responsibility: finds and ranks relevant papers.

Searches arXiv for the topic, downloads each paper's PDF into
config.PDF_DIR, extracts + chunks + embeds the text into the "papers_v1"
Chroma collection, then deletes that PDF immediately - PDFs never sit
around any longer than it takes to ingest them.

arXiv itself rate-limits (HTTP 429) or occasionally 503s under load,
independent of anything on our end. This is handled with an outer
retry-with-backoff loop around the search call, on top of the arxiv
library's own built-in retries, so a single rate-limit response doesn't
crash the whole pipeline into a 500 - it backs off and tries again, and
only gives up gracefully (empty paper list + a soft error) after exhausting
retries.
"""
import logging
import os
import re
import time
import uuid

import arxiv
import requests
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import MAX_PAPERS, PDF_DIR, CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_PAPERS
from vectorstore import get_collection
from state import ResearchState

logger = logging.getLogger("literature_agent")

ARXIV_MAX_ATTEMPTS = 4
ARXIV_BACKOFF_SECONDS = [10, 20, 40]  # wait times between attempts 1->2, 2->3, 3->4


def _safe_filename(text: str, max_len: int = 60) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)
    return text[:max_len].strip("_") or "paper"


def _search_arxiv(topic: str, max_results: int):
    # delay_seconds/num_retries configure the arxiv library's own built-in
    # retry behavior per page request; the outer loop in run() below adds a
    # second layer of retry for when arXiv is rate-limiting hard enough that
    # even those internal retries get exhausted.
    client = arxiv.Client(page_size=50, delay_seconds=5.0, num_retries=3)
    search = arxiv.Search(query=topic, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    papers = []
    for result in client.results(search):
        papers.append({
            "paper_id": result.entry_id.split("/")[-1],
            "title": result.title.strip().replace("\n", " "),
            "authors": [a.name for a in result.authors],
            "year": result.published.year if result.published else None,
            "source": "arxiv",
            "abstract": result.summary.strip().replace("\n", " "),
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
        })
    return papers


def _search_arxiv_with_retry(topic: str, max_results: int, state: ResearchState):
    """
    Wraps _search_arxiv with an outer backoff loop for arXiv rate limits
    (HTTP 429) or transient server errors (503) that survive the arxiv
    library's own internal retries. Returns whatever it managed to get -
    an empty list if every attempt failed, never raises.
    """
    last_error = None
    for attempt in range(1, ARXIV_MAX_ATTEMPTS + 1):
        try:
            return _search_arxiv(topic, max_results)
        except arxiv.HTTPError as e:
            last_error = e
            if attempt == ARXIV_MAX_ATTEMPTS:
                break
            wait = ARXIV_BACKOFF_SECONDS[min(attempt - 1, len(ARXIV_BACKOFF_SECONDS) - 1)]
            logger.warning(
                "arXiv request failed (attempt %d/%d): %s - waiting %ds before retrying",
                attempt, ARXIV_MAX_ATTEMPTS, e, wait,
            )
            time.sleep(wait)
        except Exception as e:
            # Any other unexpected error (network blip, parsing issue, etc.)
            # - don't retry indefinitely on something that might not be
            # transient, but don't crash the pipeline either.
            last_error = e
            logger.warning("arXiv search failed with an unexpected error: %s", e)
            break

    logger.error("arXiv search exhausted all retries for topic '%s': %s", topic, last_error)
    state.setdefault("errors", []).append(
        f"Literature Agent: arXiv is rate-limiting or unavailable right now "
        f"({last_error}). Try again in a minute or two."
    )
    return []


def _download_pdf(paper: dict):
    if not paper.get("pdf_url"):
        return None
    os.makedirs(PDF_DIR, exist_ok=True)
    fpath = os.path.join(PDF_DIR, f"{_safe_filename(paper['paper_id'])}.pdf")
    try:
        resp = requests.get(paper["pdf_url"], timeout=30)
        resp.raise_for_status()
        with open(fpath, "wb") as f:
            f.write(resp.content)
        return fpath
    except Exception as e:
        logger.warning("PDF download failed for %s: %s", paper["paper_id"], e)
        return None


def _extract_text(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        logger.warning("PDF text extraction failed for %s: %s", pdf_path, e)
        return ""


def run(state: ResearchState) -> ResearchState:
    topic = state["topic"]
    logger.info("Literature Agent: searching arXiv for '%s'", topic)

    papers = _search_arxiv_with_retry(topic, MAX_PAPERS, state)
    if not papers:
        state["papers"] = []
        if not any("Literature Agent" in e for e in state.get("errors", [])):
            state.setdefault("errors", []).append("Literature Agent: no papers found.")
        return state

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    collection = get_collection(COLLECTION_PAPERS)

    for paper in papers:
        pdf_path = _download_pdf(paper)
        text = _extract_text(pdf_path) if pdf_path else ""
        paper["pdf_downloaded"] = bool(text)
        source_text = text if text else paper["abstract"]

        chunks = splitter.split_text(source_text)
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "year": paper["year"] or 0,
                    "url": paper["url"],
                    "chunk_index": i,
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        ids = [f"{paper['paper_id']}_{i}_{uuid.uuid4().hex[:6]}" for i in range(len(docs))]
        if docs:
            collection.add_documents(docs, ids=ids)

        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)  # PDF is disposable once embedded

    logger.info("Literature Agent: ingested %d papers into '%s'", len(papers), COLLECTION_PAPERS)
    state["papers"] = papers
    return state
