"""
RAG Retrieve Agent - runs right after the Literature Agent and before the
Paper Analysis Agent.

Pipeline order: Literature -> RAG Retrieve -> Analysis -> Gap -> ...

Responsibility: take a specific question from the user (separate from the
broad topic used for the arXiv search) and narrow the paper set down to
just the ones actually relevant to that question, *before* the expensive
per-paper Analysis Agent step runs on them.

Why here and not after Analysis: the Literature Agent can pull in dozens of
papers on a broad topic, but Analysis makes one LLM call per paper - doing
that for every paper regardless of relevance wastes API quota (this is what
caused Groq rate-limit errors on a 15-50 paper run) and slows everything
down. Filtering first means Analysis only spends calls on papers that
matter to the actual question.

If the user doesn't supply a question, this falls back to the original
topic, so it still acts as a light relevance filter over what the
Literature Agent found rather than a no-op.
"""
import logging

from config import COLLECTION_PAPERS, TOP_K_RELEVANT_PAPERS, CHUNK_SEARCH_K
from vectorstore import get_collection
from state import ResearchState

logger = logging.getLogger("rag_agent")


def run(state: ResearchState) -> ResearchState:
    question = (state.get("question") or "").strip() or state.get("topic", "")
    state["question"] = question

    papers = state.get("papers", [])
    if not question or not papers:
        state["relevant_paper_ids"] = [p["paper_id"] for p in papers]  # nothing to filter by
        state["retrieved_context"] = []
        return state

    papers_collection = get_collection(COLLECTION_PAPERS)

    # Pull a wide pool of chunk hits, then collapse to unique paper_ids in
    # relevance order so we get the most relevant *papers*, not just the
    # most relevant individual chunks (which could all come from 2-3 papers).
    hits = papers_collection.similarity_search(question, k=CHUNK_SEARCH_K)

    seen = set()
    relevant_paper_ids = []
    for d in hits:
        pid = d.metadata.get("paper_id")
        if pid and pid not in seen:
            seen.add(pid)
            relevant_paper_ids.append(pid)
        if len(relevant_paper_ids) >= TOP_K_RELEVANT_PAPERS:
            break

    # Keep a handful of the actual passages too - useful later for the Gap
    # Agent to ground its "evidence" text on real excerpts.
    retrieved_context = [
        {"paper_id": d.metadata.get("paper_id"), "title": d.metadata.get("title"), "content": d.page_content}
        for d in hits[:10]
    ]

    if not relevant_paper_ids:
        # No chunk hits at all (e.g. every paper fell back to abstract-only
        # ingestion and embeddings genuinely don't match) - don't block the
        # pipeline, just proceed with everything the Literature Agent found.
        relevant_paper_ids = [p["paper_id"] for p in papers]
        state.setdefault("errors", []).append(
            "RAG Retrieve Agent: no relevant chunks found for this question - "
            "falling back to analyzing every paper found."
        )

    logger.info(
        "RAG Retrieve Agent: question='%s' -> %d/%d papers selected for analysis",
        question, len(relevant_paper_ids), len(papers),
    )

    state["relevant_paper_ids"] = relevant_paper_ids
    state["retrieved_context"] = retrieved_context
    return state
