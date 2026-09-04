"""
Supervisor Agent + LangGraph orchestration.

The Supervisor is the graph's entry node: it resets storage for the new
query (fresh Chroma DB + empty PDF folder) so nothing from a previous
query leaks in, then hands off through the rest of the pipeline.
"""
import logging

from langgraph.graph import StateGraph, END

from state import ResearchState
import db_manager
from agents import (
    literature_agent,
    analysis_agent,
    rag_agent,
    gap_agent,
    hypothesis_agent,
    experiment_agent,
    verification_agent,
    report_agent,
)

logger = logging.getLogger("supervisor")


def supervisor_node(state: ResearchState) -> ResearchState:
    logger.info("Supervisor: starting new query -> resetting DB + PDF store")
    db_manager.reset_for_new_query()
    state.setdefault("errors", [])
    return state


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("literature", literature_agent.run)
    graph.add_node("rag", rag_agent.run)
    graph.add_node("analysis", analysis_agent.run)
    graph.add_node("gap", gap_agent.run)
    graph.add_node("hypothesis", hypothesis_agent.run)
    graph.add_node("experiment", experiment_agent.run)
    graph.add_node("verification", verification_agent.run)
    graph.add_node("report", report_agent.run)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "literature")
    graph.add_edge("literature", "rag")
    graph.add_edge("rag", "analysis")
    graph.add_edge("analysis", "gap")
    graph.add_edge("gap", "hypothesis")
    graph.add_edge("hypothesis", "experiment")
    graph.add_edge("experiment", "verification")
    graph.add_edge("verification", "report")
    graph.add_edge("report", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(topic: str, question: str = "") -> ResearchState:
    graph = get_graph()
    final_state = graph.invoke({"topic": topic, "question": question})
    db_manager.clear_pdfs()  # safety-net sweep in case a run errored mid-way
    return final_state
