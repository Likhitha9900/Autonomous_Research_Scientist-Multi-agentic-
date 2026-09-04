import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

import db_manager
import sessions
import report_store
import chat_store
import pdf_export
from agents import (
    literature_agent,
    analysis_agent,
    rag_agent,
    gap_agent,
    hypothesis_agent,
    experiment_agent,
    verification_agent,
    report_agent,
    chat_agent,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("main")

app = FastAPI(
    title="Autonomous Research Scientist",
    description=(
        "Multi-agent RAG pipeline, exposed step-by-step: call /start with a "
        "topic, then trigger each agent endpoint in order using the run_id "
        "it gives you. Each step reads the state left behind by the step "
        "before it, runs its own agent, and returns just that agent's output."
    ),
    version="2.1.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class StartRequest(BaseModel):
    topic: str


class StartResponse(BaseModel):
    run_id: str
    topic: str
    message: str


class RagRequest(BaseModel):
    question: str | None = None  # if omitted, falls back to the original topic


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    run_id: str
    question: str
    answer: str
    saved_at: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Autonomous Research Scientist",
        "flow": [
            "POST /start",
            "POST /run/literature/{run_id}",
            "POST /run/rag/{run_id}          <- optional body: {\"question\": \"...\"}, narrows down which papers get analyzed",
            "POST /run/analysis/{run_id}",
            "POST /run/gap/{run_id}",
            "POST /run/hypothesis/{run_id}",
            "POST /run/experiment/{run_id}",
            "POST /run/verification/{run_id}",
            "POST /run/report/{run_id}",
            "GET  /reports              <- list all past reports (persists across restarts)",
            "GET  /reports/{run_id}     <- full text of one past report",
            "GET  /reports/{run_id}/pdf <- same report, rendered as a downloadable PDF",
            "DELETE /reports            <- clear report history",
            "POST /chat/{run_id}        <- body: {\"question\": \"...\"}, ask anything about this run so far",
            "GET  /chat/{run_id}        <- saved chat history for this run (persists across restarts)",
            "DELETE /chat/{run_id}      <- clear chat history for this run",
        ],
    }


@app.post("/start", response_model=StartResponse)
def start(req: StartRequest):
    """
    Step 0 - Supervisor.
    Wipes the Chroma DB and PDF store from any previous run (fresh DB per
    query), creates a new run_id to track this query's state, and returns
    it. Use that run_id in every /run/... call that follows.
    """
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be empty")

    logger.info("Supervisor: starting new run for topic '%s'", req.topic)
    db_manager.reset_for_new_query()
    run_id = sessions.create_run(req.topic.strip())
    return StartResponse(
        run_id=run_id,
        topic=req.topic.strip(),
        message="Run created and storage reset. Call /run/literature/{run_id} next.",
    )


def _run_step(run_id: str, agent_module, step_name: str):
    try:
        state = sessions.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    logger.info("%s: running for run_id=%s", step_name, run_id)
    try:
        state = agent_module.run(state)
    except Exception as e:
        logger.exception("%s failed", step_name)
        raise HTTPException(status_code=500, detail=f"{step_name} failed: {e}")

    sessions.save_run(run_id, state)
    return state


@app.post("/run/literature/{run_id}")
def run_literature(run_id: str):
    """Step 1 - Literature Agent: search arXiv, download/extract/embed PDFs, delete PDFs."""
    state = _run_step(run_id, literature_agent, "Literature Agent")
    papers = state.get("papers", [])
    return {"total_papers": len(papers), "papers": papers, "errors": state.get("errors", [])}


@app.post("/run/rag/{run_id}")
def run_rag(run_id: str, req: RagRequest = RagRequest()):
    """
    Step 2 - RAG Retrieve Agent: takes the user's specific question (in the
    request body) and narrows the papers the Literature Agent found down to
    just the ones relevant to it, *before* the expensive Analysis Agent
    step runs. This is what keeps Analysis from burning an LLM call on
    every single paper regardless of relevance.

    If you don't send a question (or send an empty one), it falls back to
    the original topic from /start, so this still acts as a light relevance
    filter over the papers found rather than a no-op.
    """
    try:
        state = sessions.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    state["question"] = (req.question or "").strip() or state.get("topic", "")

    logger.info("RAG Retrieve Agent: running for run_id=%s, question='%s'", run_id, state["question"])
    try:
        state = rag_agent.run(state)
    except Exception as e:
        logger.exception("RAG Retrieve Agent failed")
        raise HTTPException(status_code=500, detail=f"RAG Retrieve Agent failed: {e}")

    sessions.save_run(run_id, state)
    retrieved = state.get("retrieved_context", [])
    return {
        "question": state.get("question", ""),
        "total_relevant_papers": len(state.get("relevant_paper_ids", [])),
        "total_retrieved_passages": len(retrieved),
        "retrieved_context": retrieved,
        "errors": state.get("errors", []),
    }


@app.post("/run/analysis/{run_id}")
def run_analysis(run_id: str):
    """Step 3 - Paper Analysis Agent: structured extraction, scoped to the papers RAG selected."""
    state = _run_step(run_id, analysis_agent, "Paper Analysis Agent")
    analyses = state.get("analyses", [])
    return {"total_analyses": len(analyses), "analyses": analyses, "errors": state.get("errors", [])}


@app.post("/run/gap/{run_id}")
def run_gap(run_id: str):
    """Step 4 - Research Gap Agent: cross-paper comparison, evidence-linked gaps."""
    state = _run_step(run_id, gap_agent, "Research Gap Agent")
    gaps = state.get("gaps", [])
    return {"total_gaps": len(gaps), "gaps": gaps, "errors": state.get("errors", [])}


@app.post("/run/hypothesis/{run_id}")
def run_hypothesis(run_id: str):
    """Step 5 - Hypothesis Agent: research question + hypothesis per gap."""
    state = _run_step(run_id, hypothesis_agent, "Hypothesis Agent")
    hypotheses = state.get("hypotheses", [])
    return {"total_hypotheses": len(hypotheses), "hypotheses": hypotheses, "errors": state.get("errors", [])}


@app.post("/run/experiment/{run_id}")
def run_experiment(run_id: str):
    """Step 6 - Experiment Agent: baselines/datasets/metrics/plan per hypothesis."""
    state = _run_step(run_id, experiment_agent, "Experiment Agent")
    experiments = state.get("experiments", [])
    return {"total_experiments": len(experiments), "experiments": experiments, "errors": state.get("errors", [])}


@app.post("/run/verification/{run_id}")
def run_verification(run_id: str):
    """Step 7 - Verification Agent: checks each gap's claim against retrieved evidence."""
    state = _run_step(run_id, verification_agent, "Verification Agent")
    return {"verification": state.get("verification", {}), "errors": state.get("errors", [])}


@app.post("/run/report/{run_id}")
def run_report(run_id: str):
    """
    Step 8 - Report Agent: assembles the final markdown report.
    Also clears the PDF store as a final cleanup sweep for this run, and
    saves the finished report to the persistent history file (report_store.py)
    so it's retrievable later via GET /reports even after a server restart.
    """
    state = _run_step(run_id, report_agent, "Report Agent")
    db_manager.clear_pdfs()
    report_text = state.get("report", "")
    if report_text:
        report_store.save_report(
            run_id=run_id,
            topic=state.get("topic", ""),
            question=state.get("question", ""),
            report_text=report_text,
        )
    return {"report": report_text, "errors": state.get("errors", [])}


@app.get("/reports")
def list_reports():
    """
    Lightweight history of every completed report (run_id, topic, question,
    timestamp) - not the full report text, so this stays fast even with a
    long history. Use GET /reports/{run_id} to fetch one in full.
    """
    return {"reports": report_store.list_reports()}


@app.get("/reports/{run_id}")
def get_report(run_id: str):
    """Full stored report (including the markdown text) for one past run_id."""
    record = report_store.get_report(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No stored report found for run_id '{run_id}'")
    return record


@app.get("/reports/{run_id}/pdf")
def get_report_pdf(run_id: str):
    """
    The same stored report, rendered as a downloadable PDF instead of raw
    markdown. Looks it up from the persistent report history (so this
    works for old runs too, not just the one currently in progress).
    """
    record = report_store.get_report(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No stored report found for run_id '{run_id}'")

    try:
        pdf_bytes = pdf_export.markdown_report_to_pdf(
            record["report"], title=f"Research Report - {record.get('topic', run_id)}"
        )
    except Exception as e:
        logger.exception("PDF export failed for run_id=%s", run_id)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")

    filename = f"research_report_{run_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/reports")
def delete_reports():
    """Permanently clears the entire report history. This does not affect the current run."""
    report_store.clear_reports()
    return {"status": "cleared"}


@app.post("/chat/{run_id}", response_model=ChatResponse)
def chat(run_id: str, req: ChatRequest):
    """
    Ask a free-form question about this run. Answered by the Chat Agent
    from whatever the pipeline has collected so far for this run_id: the
    most relevant retrieved paper/analysis excerpts (via that run's Chroma
    collections) plus any structured gaps/hypotheses/experiments/
    verification/report already sitting in this run's state. Works at any
    point in the pipeline, not just after the Report step.

    Every exchange is saved to persistent chat history (chat_store.py),
    retrievable later via GET /chat/{run_id} even after a server restart.
    """
    try:
        state = sessions.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    logger.info("Chat Agent: running for run_id=%s", run_id)
    try:
        answer = chat_agent.run(state, req.question.strip())
    except Exception as e:
        logger.exception("Chat Agent failed")
        raise HTTPException(status_code=500, detail=f"Chat Agent failed: {e}")

    record = chat_store.save_message(run_id, req.question.strip(), answer)
    return ChatResponse(
        run_id=record["run_id"],
        question=record["question"],
        answer=record["answer"],
        saved_at=record["saved_at"],
    )


@app.get("/chat/{run_id}")
def get_chat_history(run_id: str):
    """Full saved chat history (question/answer pairs) for one run_id, oldest first."""
    return {"history": chat_store.get_history(run_id)}


@app.delete("/chat/{run_id}")
def delete_chat_history(run_id: str):
    """Clears saved chat history for one run_id only. Does not affect the run itself."""
    chat_store.clear_history(run_id)
    return {"status": "cleared"}


@app.get("/state/{run_id}")
def get_state(run_id: str):
    """See everything accumulated so far for a run, at any point in the sequence."""
    try:
        return sessions.get_run(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/reset")
def reset():
    """Manually wipe the vector DB and PDF store, and clear all in-memory runs."""
    db_manager.clear_all()
    sessions.RUNS.clear()
    return {"status": "cleared"}
