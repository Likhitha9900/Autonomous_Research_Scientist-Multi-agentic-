# Autonomous Research Scientist - Backend

Multi-agent RAG pipeline: LangGraph (orchestration) + LangChain (RAG) +
Groq (LLM) + ChromaDB (vector store) + FastAPI (API).

## Agents

| Node | File | Responsibility |
|---|---|---|
| Supervisor | `graph.py` | Resets DB/PDF store for the new query, coordinates the run |
| Literature Agent | `agents/literature_agent.py` | arXiv search, PDF download, extract/chunk/embed, deletes PDF right after |
| RAG Retrieve Agent | `agents/rag_agent.py` | Takes the user's specific question, narrows the found papers down to the relevant ones *before* Analysis runs |
| Paper Analysis Agent | `agents/analysis_agent.py` | Structured methods/datasets/metrics/results/limitations - only for the papers RAG selected |
| Research Gap Agent | `agents/gap_agent.py` | Cross-paper comparison, evidence-linked gaps |
| Hypothesis Agent | `agents/hypothesis_agent.py` | Research questions + testable hypotheses per gap |
| Experiment Agent | `agents/experiment_agent.py` | Baselines/datasets/metrics/plan per hypothesis |
| Verification Agent | `agents/verification_agent.py` | Re-checks each gap's claim against retrieved evidence |
| Report Agent | `agents/report_agent.py` | Assembles the final markdown report |

## Fresh database per query

Enforced two ways:
1. `db_manager.reset_for_new_query()` — called by `/start` at the beginning
   of every new query. Deletes and recreates `data/chroma_db/` and
   `data/pdfs/` before anything else runs.
2. Inside `literature_agent.py`, each PDF is deleted immediately after its
   text is embedded — it never persists even for the length of one query.

## API flow — step through each agent manually

The API is built so you trigger each agent one at a time from the `/docs`
page (or curl/Postman) and see that agent's own output before moving to the
next one. Each step reads the state the previous step left behind — that's
the "linked together" chaining — and adds its own results on top.

| Order | Endpoint | What it returns |
|---|---|---|
| 0 | `POST /start` `{"topic": "..."}` | `run_id` — resets storage, use this id in every step below |
| 1 | `POST /run/literature/{run_id}` | `papers` found + ingested |
| 2 | `POST /run/rag/{run_id}` `{"question": "..."}` (optional body) | which papers are relevant to that question |
| 3 | `POST /run/analysis/{run_id}` | `analyses` — only for the papers RAG selected |
| 4 | `POST /run/gap/{run_id}` | `gaps` identified |
| 5 | `POST /run/hypothesis/{run_id}` | `hypotheses` per gap |
| 6 | `POST /run/experiment/{run_id}` | `experiments` per hypothesis |
| 7 | `POST /run/verification/{run_id}` | `verification` verdicts per gap |
| 8 | `POST /run/report/{run_id}` | final markdown `report` — also saved to persistent history |

## Report history — persists across restarts

Every time `/run/report/{run_id}` finishes, the report gets appended to
`data/reports_history.json` via `report_store.py`. This file lives directly
under `data/`, not inside `chroma_db/` or `pdfs/`, so it's untouched by the
per-query reset described above — it keeps every report from every query
you've ever run, until you explicitly clear it.

| Endpoint | What it does |
|---|---|
| `GET /reports` | Lightweight list of every past report: `run_id`, `topic`, `question`, `saved_at` (no report text, so this stays fast) |
| `GET /reports/{run_id}` | Full record for one past run, including the complete markdown `report` |
| `DELETE /reports` | Permanently clears the whole history (does not affect whatever run is currently in progress) |

**About the RAG Retrieve Agent (step 2) — why it runs before Analysis, not after:**
the topic you gave `/start` drives the arXiv search and can pull in far more
papers than are actually relevant to what you want to investigate. The
Analysis Agent makes one Groq call *per paper*, so analyzing every single
one regardless of relevance wastes API quota and is what caused rate-limit
errors on larger paper counts. Putting RAG here means it filters the paper
set down (`config.TOP_K_RELEVANT_PAPERS`, default 15) *before* those
expensive calls happen — Analysis then only processes papers that matter.

You can send a specific question in the body — e.g. topic = "AI in
healthcare", question = "how well do current models generalize across
hospitals?" — and only papers relevant to *that* question get analyzed and
carried through to the Gap Agent onward. If you send an empty body or skip
the question field, it falls back to the original topic, so it still acts
as a relevance filter over what the Literature Agent found rather than a
no-op — you don't have to supply a question for this step to be useful.

`GET /state/{run_id}` shows everything accumulated so far, at any point.

**In the browser (`http://127.0.0.1:8000/docs`):**
1. Expand `POST /start`, click "Try it out", enter your topic, click Execute
2. Copy the `run_id` from the response
3. Expand `POST /run/literature/{run_id}`, click "Try it out", paste the
   `run_id` into the path field, click Execute — see the papers it found
4. Expand `POST /run/rag/{run_id}`, paste the `run_id`, optionally fill in
   a `question` in the body (or leave it empty), click Execute
5. Repeat for each remaining `/run/...` endpoint in order, pasting the same
   `run_id` each time, until you reach `/run/report/{run_id}` for the final
   report

You don't have to run them all in the same sitting — the state for a
`run_id` stays in memory until you call `/start` again or `/reset`, so you
can inspect each agent's output for as long as you want before moving on.

## Setup

**Windows (cmd.exe):**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
notepad .env
```
In Notepad, replace `your_groq_api_key_here` with your real key from
https://console.groq.com (find "API Keys" in the sidebar), save, close.

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # edit GROQ_API_KEY, Ctrl+O then Enter to save, Ctrl+X to exit
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` for the interactive Swagger UI and follow
the step-by-step flow above.

`POST /reset` wipes storage and clears all in-memory runs without starting a new query.

Note: `graph.py` still contains the original LangGraph pipeline
(`run_pipeline(topic, question="")`) which runs all 8 agents automatically
end-to-end in one call if you ever want that instead — it's just not wired
into `main.py` anymore since the step-by-step flow is now the default.

## Notes

- `config.MAX_PAPERS` (default 50) controls how many arXiv results the
  Literature Agent pulls per query.
- `config.TOP_K_RELEVANT_PAPERS` (default 15) controls how many of those
  papers actually get analyzed, after the RAG Retrieve Agent ranks them by
  relevance. Lower this further if you're still hitting Groq rate limits;
  raise it for broader coverage at the cost of more API calls.
- `config.CHUNK_SEARCH_K` (default 60) is how many raw chunks the RAG
  Retrieve Agent pulls back before collapsing them to unique papers - kept
  wide so enough distinct papers are represented before ranking.
- Literature Agent sources from arXiv only for now; Semantic
  Scholar/OpenAlex/Crossref can be added as extra `_search_x()` functions
  in `literature_agent.py`, merged + deduped before the download step.
- Default Groq model is `openai/gpt-oss-120b` — change `GROQ_MODEL` in
  `.env` if you want a different one. `llm.py` also auto-retries with
  backoff on Groq 429 rate-limit responses.
- Requires Python 3.10+.
