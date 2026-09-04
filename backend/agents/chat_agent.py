"""
Chat Agent - not part of the linear pipeline (Literature -> ... -> Report).
Lets the user ask free-form questions about one run, answered from
everything that run has collected *so far*:

  - the most relevant paper excerpts and paper-analysis summaries, pulled
    from that run's Chroma collections (COLLECTION_PAPERS /
    COLLECTION_ANALYSIS - both wiped and rebuilt fresh per query, so this
    only ever surfaces material from the current run's own papers)
  - whatever structured gaps / hypotheses / experiments / verification
    verdicts / final report already exist in the run's in-memory state

This is a retriever, not another pipeline step: it can be called at any
point (even before Analysis or Report have run) and just answers from
whatever is available at that moment.
"""
import logging

from config import (
    COLLECTION_PAPERS,
    COLLECTION_ANALYSIS,
    CHAT_TOP_K_CHUNKS,
    CHAT_CHUNK_CHAR_LIMIT,
    CHAT_LIST_ITEM_CHAR_LIMIT,
    CHAT_MAX_LIST_ITEMS,
    CHAT_REPORT_CHAR_LIMIT,
)
from vectorstore import get_collection
from llm import ask
from state import ResearchState

logger = logging.getLogger("chat_agent")

SYSTEM_PROMPT = """You are the research assistant chatbot for an autonomous
multi-agent research pipeline. Answer the user's question using ONLY the
context given below - retrieved paper excerpts, paper analyses, and the
pipeline's own structured findings (gaps, hypotheses, experiment plans,
verification verdicts, final report) for this specific run. Be specific:
reference paper_ids, gap names, or hypotheses where it helps. If the
context does not contain enough information to answer, say so plainly
instead of guessing or inventing details."""


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …[truncated]"


def _format_list(label: str, items: list) -> str:
    items = [i for i in items if i]
    if not items:
        return f"{label}: none yet."
    shown = items[:CHAT_MAX_LIST_ITEMS]
    lines = [f"- {_truncate(i, CHAT_LIST_ITEM_CHAR_LIMIT)}" for i in shown]
    if len(items) > len(shown):
        lines.append(f"- …and {len(items) - len(shown)} more (not shown, ask a more specific question)")
    return f"{label}:\n" + "\n".join(lines)


def _build_structured_context(state: ResearchState) -> str:
    gaps = state.get("gaps", [])
    hypotheses = state.get("hypotheses", [])
    experiments = state.get("experiments", [])
    verification_results = state.get("verification", {}).get("results", [])
    report = state.get("report", "")

    parts = [
        f"Topic: {state.get('topic', '')}",
        _format_list("Research gaps identified", [g.get("gap") for g in gaps]),
        _format_list("Hypotheses generated", [h.get("hypothesis") for h in hypotheses]),
        _format_list("Experiment plans", [e.get("experiment_plan") for e in experiments]),
        _format_list(
            "Verification verdicts",
            [f"{v.get('gap')}: {v.get('verdict')} ({v.get('reasoning')})" for v in verification_results],
        ),
    ]
    # The full report duplicates most of what's already in the lists above,
    # so it's capped hard rather than included verbatim - keeps the prompt
    # small on small-model tiers while still letting the model answer
    # report-wording questions from the (truncated) text.
    if report:
        parts.append(f"Final assembled report (may be truncated):\n{_truncate(report, CHAT_REPORT_CHAR_LIMIT)}")
    return "\n\n".join(parts)


def _retrieve_chunks(question: str) -> list[str]:
    chunks = []
    try:
        papers_collection = get_collection(COLLECTION_PAPERS)
        paper_hits = papers_collection.similarity_search(question, k=CHAT_TOP_K_CHUNKS)
        chunks.extend(
            f"[paper:{d.metadata.get('paper_id', '?')}] {_truncate(d.page_content, CHAT_CHUNK_CHAR_LIMIT)}"
            for d in paper_hits
        )
    except Exception:
        logger.exception("Chat Agent: retrieval from %s failed - skipping", COLLECTION_PAPERS)

    try:
        analysis_collection = get_collection(COLLECTION_ANALYSIS)
        analysis_hits = analysis_collection.similarity_search(question, k=CHAT_TOP_K_CHUNKS)
        chunks.extend(
            f"[analysis:{d.metadata.get('paper_id', '?')}] {_truncate(d.page_content, CHAT_CHUNK_CHAR_LIMIT)}"
            for d in analysis_hits
        )
    except Exception:
        logger.exception("Chat Agent: retrieval from %s failed - skipping", COLLECTION_ANALYSIS)

    return chunks


def run(state: ResearchState, question: str) -> str:
    question = (question or "").strip()
    if not question:
        return "Ask me something specific about this run's papers, gaps, hypotheses, experiments, or report."

    retrieved_chunks = _retrieve_chunks(question)
    chunk_context = "\n\n".join(retrieved_chunks) if retrieved_chunks else "No retrieved passages matched this question."
    structured_context = _build_structured_context(state)

    user_prompt = (
        f"Question: {question}\n\n"
        f"--- Structured pipeline findings for this run ---\n{structured_context}\n\n"
        f"--- Retrieved passages (papers + analyses) ---\n{chunk_context}"
    )

    logger.info(
        "Chat Agent: answering question='%s' (prompt ~%d chars, ~%d est. tokens)",
        question, len(user_prompt), len(user_prompt) // 4,
    )
    return ask(SYSTEM_PROMPT, user_prompt)
