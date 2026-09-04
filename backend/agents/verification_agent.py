"""
Agent 6 - Verification Agent
Responsibility: checks claims against source evidence.

For each proposed gap, re-retrieves the top matching chunks from the
vector store for its supporting_paper_ids and asks the LLM whether the
gap's "evidence" claim is actually supported by those passages.
"""
import logging

from config import COLLECTION_PAPERS
from vectorstore import get_collection
from llm import ask_json
from state import ResearchState

logger = logging.getLogger("verification_agent")

SYSTEM_PROMPT = """You are the Verification Agent in a scientific research pipeline.
You will be shown a claimed research gap plus retrieved source passages.
Judge strictly whether the passages actually support the claim."""

SCHEMA_HINT = """Return JSON:
{"verdict": "supported" | "partially_supported" | "unsupported",
 "reasoning": "one sentence explanation"}"""


def _retrieve_evidence(collection, query: str, paper_ids, k: int = 4):
    if not paper_ids:
        return collection.similarity_search(query, k=k)
    docs = []
    for pid in paper_ids:
        docs.extend(collection.similarity_search(query, k=2, filter={"paper_id": pid}))
    return docs


def run(state: ResearchState) -> ResearchState:
    gaps = state.get("gaps", [])
    if not gaps:
        state["verification"] = {"checked": 0, "results": []}
        return state

    collection = get_collection(COLLECTION_PAPERS)
    results = []
    for gap in gaps:
        query = gap.get("gap", "")
        paper_ids = gap.get("supporting_paper_ids", [])
        evidence_docs = _retrieve_evidence(collection, query, paper_ids)
        evidence_text = "\n---\n".join(d.page_content for d in evidence_docs) or "(no evidence retrieved)"

        user_prompt = (
            f"Claimed gap: {gap.get('gap')}\n"
            f"Claimed evidence: {gap.get('evidence')}\n\n"
            f"Retrieved passages:\n{evidence_text}\n\n{SCHEMA_HINT}"
        )
        try:
            verdict = ask_json(SYSTEM_PROMPT, user_prompt, raise_on_failure=True)
            if not isinstance(verdict, dict) or "verdict" not in verdict:
                raise RuntimeError(f"expected a JSON object with a 'verdict' key, got: {str(verdict)[:200]}")
        except Exception as e:
            logger.warning("Verification Agent: could not verify gap '%s' (%s)", gap.get("gap"), e)
            state.setdefault("errors", []).append(
                f"Verification Agent: could not verify gap '{gap.get('gap')}' - model output was not valid JSON"
            )
            verdict = {"verdict": "unverified", "reasoning": "Model output could not be parsed - not a real judgment."}
        results.append({"gap": gap.get("gap"), **verdict})

    logger.info("Verification Agent: checked %d gaps", len(results))
    state["verification"] = {"checked": len(results), "results": results}
    return state
