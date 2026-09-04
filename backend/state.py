from typing import TypedDict, List, Dict, Any


class ResearchState(TypedDict, total=False):
    topic: str
    papers: List[Dict[str, Any]]
    analyses: List[Dict[str, Any]]
    question: str                       # user's specific question for the RAG Retrieve Agent
    retrieved_context: List[Dict[str, Any]]  # passages the RAG Agent pulled for that question
    relevant_paper_ids: List[str]       # paper_ids the RAG Agent judged relevant to the question
    gaps: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    experiments: List[Dict[str, Any]]
    verification: Dict[str, Any]
    report: str
    errors: List[str]
