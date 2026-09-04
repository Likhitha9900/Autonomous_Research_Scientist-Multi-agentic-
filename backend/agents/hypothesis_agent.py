"""
Agent 4 - Hypothesis Agent
Responsibility: creates research questions and hypotheses.
"""
import logging
from llm import ask_json
from state import ResearchState

logger = logging.getLogger("hypothesis_agent")

SYSTEM_PROMPT = """You are the Hypothesis Agent in a scientific research pipeline.
Convert each given research gap into a concrete, testable research question
and hypothesis. Stay grounded in the gap provided."""

SCHEMA_HINT = """Return a JSON array, one item per input gap, each item:
{
  "gap": "the gap this hypothesis addresses (copy from input)",
  "research_question": "a specific, answerable research question",
  "hypothesis": "a testable hypothesis statement",
  "supporting_paper_ids": ["..."]
}"""


def run(state: ResearchState) -> ResearchState:
    gaps = state.get("gaps", [])
    if not gaps:
        state["hypotheses"] = []
        return state

    gaps_text = "\n\n".join(
        f"gap: {g.get('gap')}\nevidence: {g.get('evidence')}\n"
        f"supporting_paper_ids: {g.get('supporting_paper_ids')}"
        for g in gaps
    )
    user_prompt = f"Topic: {state['topic']}\n\nResearch gaps:\n{gaps_text}\n\n{SCHEMA_HINT}"

    hypotheses = ask_json(SYSTEM_PROMPT, user_prompt, raise_on_failure=True)
    if not isinstance(hypotheses, list):
        raise RuntimeError(f"expected a JSON array of hypotheses, got {type(hypotheses).__name__}: {str(hypotheses)[:200]}")

    logger.info("Hypothesis Agent: generated %d hypotheses", len(hypotheses))
    state["hypotheses"] = hypotheses
    return state
