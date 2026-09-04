"""
Agent 7 - Report Agent
Responsibility: produces the final structured research report.

Deterministic assembly (so citations stay traceable to real paper_ids)
plus one LLM call to write a short narrative executive summary.
"""
import logging
from llm import ask
from state import ResearchState

logger = logging.getLogger("report_agent")

SYSTEM_PROMPT = """You are the Report Agent. Write a concise (4-6 sentence)
executive summary for a literature-review research report, based only on
the structured findings given to you. Do not invent findings."""


def _papers_section(papers):
    if not papers:
        return "_No papers retrieved._"
    return "\n".join(f"- **{p['title']}** ({p.get('year', 'n.d.')}) - `{p['paper_id']}`" for p in papers)


def _gaps_section(gaps, verification_results):
    if not gaps:
        return "_No gaps identified._"
    verdict_map = {v["gap"]: v for v in verification_results}
    lines = []
    for g in gaps:
        v = verdict_map.get(g.get("gap"), {})
        lines.append(
            f"- **Gap:** {g.get('gap')}\n"
            f"  - Evidence: {g.get('evidence')}\n"
            f"  - Supporting papers: {', '.join(g.get('supporting_paper_ids', [])) or 'none'}\n"
            f"  - Verification: **{v.get('verdict', 'not checked')}**"
        )
    return "\n".join(lines)


def _hypotheses_section(hypotheses, experiments):
    if not hypotheses:
        return "_No hypotheses generated._"
    exp_map = {e.get("hypothesis"): e for e in experiments}
    lines = []
    for h in hypotheses:
        e = exp_map.get(h.get("hypothesis"), {})
        lines.append(
            f"- **Research question:** {h.get('research_question')}\n"
            f"  - Hypothesis: {h.get('hypothesis')}\n"
            f"  - Baselines: {', '.join(e.get('baselines', [])) or 'n/a'}\n"
            f"  - Datasets: {', '.join(e.get('datasets', [])) or 'n/a'}\n"
            f"  - Metrics: {', '.join(e.get('metrics', [])) or 'n/a'}\n"
            f"  - Plan: {e.get('experiment_plan', 'n/a')}"
        )
    return "\n".join(lines)


def run(state: ResearchState) -> ResearchState:
    papers = state.get("papers", [])
    analyses = state.get("analyses", [])
    gaps = state.get("gaps", [])
    hypotheses = state.get("hypotheses", [])
    experiments = state.get("experiments", [])
    verification = state.get("verification", {"results": []})

    findings_summary = (
        f"{len(papers)} papers retrieved, {len(analyses)} analyzed, "
        f"{len(gaps)} gaps identified, {len(hypotheses)} hypotheses generated."
    )
    exec_summary = ask(
        SYSTEM_PROMPT,
        f"Topic: {state['topic']}\n\nFindings summary: {findings_summary}\n\n"
        f"Top gaps: {[g.get('gap') for g in gaps[:3]]}",
    )

    report = f"""# Research Report: {state['topic']}

## Executive Summary
{exec_summary}

## Papers Reviewed ({len(papers)})
{_papers_section(papers)}

## Identified Research Gaps
{_gaps_section(gaps, verification.get("results", []))}

## Hypotheses & Experiment Plans
{_hypotheses_section(hypotheses, experiments)}

## Pipeline Notes
{findings_summary}
"""
    if state.get("errors"):
        report += "\n## Warnings\n" + "\n".join(f"- {e}" for e in state["errors"])

    logger.info("Report Agent: report generated (%d chars)", len(report))
    state["report"] = report
    return state
