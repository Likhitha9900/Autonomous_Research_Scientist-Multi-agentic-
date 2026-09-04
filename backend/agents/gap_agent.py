"""
Agent - Research Gap Agent
Responsibility: compares studies and proposes evidence-based gaps.

Pipeline order: Literature -> RAG Retrieve -> Analysis -> Gap -> ...
By the time this runs, `analyses` already only contains the papers the RAG
Retrieve Agent judged relevant (Analysis only processes that subset), so
the relevant_paper_ids filter below is mostly a defensive no-op - it still
matters if analyses somehow includes more than what RAG selected, or if RAG
was skipped entirely, in which case this falls back to using every
analyzed paper, exactly like before. `retrieved_context` (the actual
passages RAG pulled) is used here to ground each gap's evidence text.
"""
import logging
from llm import ask_json
from state import ResearchState

logger = logging.getLogger("gap_agent")

SYSTEM_PROMPT = """You are the Research Gap Agent in a scientific literature review pipeline.
Compare the given paper analyses to find repeated limitations, under-tested
assumptions, missing datasets, or unexplored method combinations. Every gap
must be traceable to specific paper_ids from the input - do not invent gaps
that aren't supported by the given analyses. If a specific research question
is given, prioritize gaps that are directly relevant to answering it."""

SCHEMA_HINT = """Return a JSON array. Each item:
{
  "gap": "short description of the research gap",
  "evidence": "why the analyses support this gap",
  "supporting_paper_ids": ["paper_id1", "paper_id2"]
}
Return 3-6 gaps, ordered from most to least significant."""


def run(state: ResearchState) -> ResearchState:
    analyses = state.get("analyses", [])
    if not analyses:
        state["gaps"] = []
        return state

    relevant_ids = set(state.get("relevant_paper_ids", []) or [])
    focused_analyses = [a for a in analyses if a["paper_id"] in relevant_ids] if relevant_ids else []
    # Fall back to the full set if RAG didn't run or found nothing relevant
    scoped_analyses = focused_analyses or analyses

    condensed = "\n\n".join(
        f"paper_id: {a['paper_id']}\ntitle: {a['title']}\n"
        f"methods: {a.get('methods')}\ndatasets: {a.get('datasets')}\n"
        f"metrics: {a.get('metrics')}\nresults: {a.get('results')}\n"
        f"limitations: {a.get('limitations')}"
        for a in scoped_analyses
    )

    question = state.get("question")
    header = f"Topic: {state['topic']}"
    if question and question != state["topic"]:
        header += f"\nSpecific question to focus on: {question}"

    retrieved_context = state.get("retrieved_context", [])
    context_block = ""
    if retrieved_context:
        passages = "\n---\n".join(
            f"[{c.get('paper_id')}] {c.get('content')}" for c in retrieved_context
        )
        context_block = f"\n\nRetrieved supporting passages:\n{passages}"

    user_prompt = f"{header}\n\nPaper analyses:\n{condensed}{context_block}\n\n{SCHEMA_HINT}"

    gaps = ask_json(SYSTEM_PROMPT, user_prompt, raise_on_failure=True)
    if not isinstance(gaps, list):
        raise RuntimeError(f"expected a JSON array of gaps, got {type(gaps).__name__}: {str(gaps)[:200]}")

    logger.info("Gap Agent: identified %d gaps (scoped to %d/%d papers)",
                len(gaps), len(scoped_analyses), len(analyses))
    state["gaps"] = gaps
    return state
