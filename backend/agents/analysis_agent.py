"""
Agent - Paper Analysis Agent
Responsibility: extracts structured information from papers.

Pipeline order: Literature -> RAG Retrieve -> Analysis -> Gap -> ...
If the RAG Retrieve Agent ran before this (the default pipeline order),
only the papers it judged relevant to the user's question get analyzed -
that's what keeps this step from burning one LLM call per paper on papers
that don't actually matter, which is what previously caused Groq rate-limit
errors on larger paper sets. If relevant_paper_ids is empty (RAG didn't
run), it falls back to analyzing every paper, exactly like before.
"""
import logging

from config import COLLECTION_PAPERS, COLLECTION_ANALYSIS
from vectorstore import get_collection
from llm import ask_json
from state import ResearchState
from langchain_core.documents import Document

logger = logging.getLogger("analysis_agent")

SYSTEM_PROMPT = """You are the Paper Analysis Agent in a research pipeline.
Given excerpts from one academic paper, extract structured information.
Only use information present in the excerpts - do not invent details."""

SCHEMA_HINT = """Return a JSON object with exactly these keys:
{
  "methods": ["..."],
  "datasets": ["..."],
  "metrics": ["..."],
  "results": "one or two sentence summary of key results",
  "limitations": ["..."]
}
If a field cannot be determined, use an empty list or "unknown"."""


def _get_paper_chunks(collection, paper_id: str):
    result = collection.get(where={"paper_id": paper_id})
    return result.get("documents", [])


def run(state: ResearchState) -> ResearchState:
    all_papers = state.get("papers", [])
    if not all_papers:
        state["analyses"] = []
        return state

    relevant_ids = set(state.get("relevant_paper_ids", []) or [])
    papers = [p for p in all_papers if p["paper_id"] in relevant_ids] if relevant_ids else all_papers

    papers_collection = get_collection(COLLECTION_PAPERS)
    analysis_collection = get_collection(COLLECTION_ANALYSIS)

    analyses = []
    for paper in papers:
        chunks = _get_paper_chunks(papers_collection, paper["paper_id"])
        if not chunks:
            continue
        context = "\n\n".join(chunks[:8])

        user_prompt = f"Paper title: {paper['title']}\n\nExcerpts:\n{context}\n\n{SCHEMA_HINT}"
        result = ask_json(SYSTEM_PROMPT, user_prompt, default={})
        if not result:
            state.setdefault("errors", []).append(f"Analysis Agent: failed to parse output for {paper['paper_id']}")
            continue

        result["paper_id"] = paper["paper_id"]
        result["title"] = paper["title"]
        analyses.append(result)

        summary_text = (
            f"Title: {paper['title']}\n"
            f"Methods: {', '.join(result.get('methods', []))}\n"
            f"Datasets: {', '.join(result.get('datasets', []))}\n"
            f"Metrics: {', '.join(result.get('metrics', []))}\n"
            f"Results: {result.get('results', '')}\n"
            f"Limitations: {', '.join(result.get('limitations', []))}"
        )
        analysis_collection.add_documents(
            [Document(page_content=summary_text, metadata={"paper_id": paper["paper_id"], "title": paper["title"]})],
            ids=[f"analysis_{paper['paper_id']}"],
        )

    logger.info("Analysis Agent: analyzed %d/%d selected papers (%d found in total)",
                len(analyses), len(papers), len(all_papers))
    state["analyses"] = analyses
    return state
