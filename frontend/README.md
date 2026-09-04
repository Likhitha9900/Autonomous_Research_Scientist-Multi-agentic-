# Autonomous Research Scientist — React Frontend

A React + Vite dashboard for the FastAPI backend. Same idea as the earlier
plain-HTML version, rebuilt as a proper React app, and updated to match the
current backend: Literature → RAG Retrieve → Analysis → Gap → Hypothesis →
Experiment → Verification → Report, plus a Report History tab for the
backend's persisted report store.

## Setup

Requires [Node.js](https://nodejs.org) 18+ and npm.

```bash
cd frontend
npm install
npm run dev
```

Vite will print a local URL, usually `http://localhost:5173` — open that in
your browser.

Make sure the backend is running first (`uvicorn main:app --reload --port 8000`
in the `backend` folder) — the app defaults to `http://127.0.0.1:8000` and
you can change that from the input box in the header if yours is different.

## Project structure

```
frontend/
  index.html
  vite.config.js
  package.json
  src/
    main.jsx              entry point
    App.jsx                top-level state + orchestration
    api.js                 one function per backend endpoint
    markdown.js             tiny markdown -> HTML renderer for the report
    styles.css
    components/
      Stepper.jsx           visual progress indicator (9 steps)
      Common.jsx             Chips / VerdictBadge / Warnings / etc.
      LiteratureSection.jsx
      RagSection.jsx         includes the question input box
      AnalysisSection.jsx
      GapSection.jsx
      HypothesisSection.jsx
      ExperimentSection.jsx
      VerificationSection.jsx
      ReportSection.jsx       markdown render + Download report.md
      ReportHistory.jsx       browses GET /reports (persisted history)
```

## How to use it

**Pipeline tab:**
1. Type a topic, click **Start (Supervisor)** — resets the backend's
   storage and gives you a `run_id`.
2. Click each agent's **Run ... Agent** button in order, or use
   **Run all remaining steps** to chain them automatically. Each section
   only appears once you've run that step at least once.
3. The **RAG Retrieve** section has its own question box — type a specific
   question there before running it to narrow which papers the Analysis
   Agent processes (leave it blank to just use your topic).
4. Any errors an agent reports show as an amber warning under that section
   instead of failing silently.
5. Once the Report Agent runs, you get the rendered report plus a
   **Download report.md** button. It's also automatically saved to the
   backend's persistent history.

**Report History tab:**
- Lists every report ever generated (persists across backend restarts).
- Click any entry to load and read its full text.
- **Delete all history** permanently clears it (confirmation required).

**Reset everything** wipes the backend's storage, clears the whole page,
and lets you start a new topic from scratch.

## Building for production

```bash
npm run build
```

Outputs static files to `dist/` — you can serve those with any static file
host if you want something more permanent than the Vite dev server. The
backend's CORS is already wide open (`allow_origins=["*"]`), so this works
regardless of what origin serves the frontend.

## Notes

- No state management library — everything lives in `App.jsx`'s `useState`,
  passed down as props. Simple enough not to need Redux/Zustand for a
  single-page dashboard like this.
- The markdown renderer in `markdown.js` is intentionally minimal (headers,
  bold, inline code, lists, paragraphs) — just enough for the Report
  Agent's output format, not a general-purpose markdown parser.
- If you jump ahead (e.g. run Gap before Analysis), each section shows an
  explanatory empty state instead of a blank page, telling you which
  earlier step to run first.
