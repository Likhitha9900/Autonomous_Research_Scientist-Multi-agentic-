"""
Very small in-memory store that holds a ResearchState between separate
step-by-step API calls (since HTTP requests are stateless, we need
somewhere to keep the state a run is building up as you call each agent
endpoint one at a time).

Not meant for production/multi-worker deployment - it's a single process
dict, which is exactly right for one person clicking through /docs locally.
"""
import uuid
from typing import Dict

from state import ResearchState

RUNS: Dict[str, ResearchState] = {}


def create_run(topic: str) -> str:
    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {"topic": topic, "errors": []}
    return run_id


def get_run(run_id: str) -> ResearchState:
    if run_id not in RUNS:
        raise KeyError(f"No run found with id '{run_id}'. Call /start first.")
    return RUNS[run_id]


def save_run(run_id: str, state: ResearchState):
    RUNS[run_id] = state


def delete_run(run_id: str):
    RUNS.pop(run_id, None)
