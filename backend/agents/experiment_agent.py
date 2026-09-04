"""
Agent 5 - Experiment Agent
Responsibility: suggests datasets, baselines, metrics and experiments.
"""
import logging
from llm import ask_json
from state import ResearchState

logger = logging.getLogger("experiment_agent")

SYSTEM_PROMPT = """You are the Experiment Agent in a scientific research pipeline.
For each hypothesis, design a practical experiment plan: baselines to compare
against, datasets to use (reuse ones mentioned in the source papers where
sensible), and evaluation metrics. Keep plans realistic for an academic/
internship-scale project."""

SCHEMA_HINT = """Return a JSON array, one item per input hypothesis:
{
  "hypothesis": "copy from input",
  "baselines": ["..."],
  "datasets": ["..."],
  "metrics": ["..."],
  "experiment_plan": "2-4 sentence description of the experimental setup"
}"""


def run(state: ResearchState) -> ResearchState:
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        state["experiments"] = []
        return state

    hyp_text = "\n\n".join(
        f"research_question: {h.get('research_question')}\nhypothesis: {h.get('hypothesis')}"
        for h in hypotheses
    )
    user_prompt = f"Topic: {state['topic']}\n\nHypotheses:\n{hyp_text}\n\n{SCHEMA_HINT}"

    experiments = ask_json(SYSTEM_PROMPT, user_prompt, raise_on_failure=True)
    if not isinstance(experiments, list):
        raise RuntimeError(f"expected a JSON array of experiment plans, got {type(experiments).__name__}: {str(experiments)[:200]}")

    logger.info("Experiment Agent: designed %d experiment plans", len(experiments))
    state["experiments"] = experiments
    return state
