import { useEffect, useRef, useState } from "react";
import {
  checkHealth,
  startRun,
  runLiterature,
  runRag,
  runAnalysis,
  runGap,
  runHypothesis,
  runExperiment,
  runVerification,
  runReport,
  resetAll,
} from "./api.js";
import Stepper, { STEP_ORDER } from "./components/Stepper.jsx";
import LiteratureSection from "./components/LiteratureSection.jsx";
import RagSection from "./components/RagSection.jsx";
import AnalysisSection from "./components/AnalysisSection.jsx";
import GapSection from "./components/GapSection.jsx";
import HypothesisSection from "./components/HypothesisSection.jsx";
import ExperimentSection from "./components/ExperimentSection.jsx";
import VerificationSection from "./components/VerificationSection.jsx";
import ReportSection from "./components/ReportSection.jsx";
import ReportHistory from "./components/ReportHistory.jsx";
import ChatPanel from "./components/ChatPanel.jsx";

// Maps a step key to its API call (all take (backendUrl, runId) except
// "rag", which also needs the question - handled specially in runStep).
const STEP_API = {
  literature: runLiterature,
  analysis: runAnalysis,
  gap: runGap,
  hypothesis: runHypothesis,
  experiment: runExperiment,
  verification: runVerification,
  report: runReport,
};

export default function App() {
  const [backendUrl, setBackendUrl] = useState("http://127.0.0.1:8000");
  const [connected, setConnected] = useState(false);
  const [view, setView] = useState("pipeline"); // "pipeline" | "history"

  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [runId, setRunId] = useState(null);

  const [stepStatus, setStepStatus] = useState({});
  const [results, setResults] = useState({});
  const [globalError, setGlobalError] = useState("");
  const [runningAll, setRunningAll] = useState(false);

  const stepStatusRef = useRef(stepStatus);
  stepStatusRef.current = stepStatus;

  const setStatus = (key, status) => setStepStatus((prev) => ({ ...prev, [key]: status }));

  const checkConn = async () => {
    try {
      await checkHealth(backendUrl);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  };

  useEffect(() => {
    checkConn();
    const id = setInterval(checkConn, 8000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendUrl]);

  const handleStart = async () => {
    if (!topic.trim()) {
      setGlobalError("Enter a research topic first.");
      return;
    }
    setGlobalError("");
    setStatus("start", "running");
    try {
      const data = await startRun(backendUrl, topic.trim());
      setRunId(data.run_id);
      setStepStatus({ start: "done" });
      setResults({});
    } catch (e) {
      setStatus("start", "error");
      setGlobalError("Start failed: " + e.message);
    }
  };

  // Returns true on success, false on failure (so runAll can stop the chain).
  const runStep = async (key) => {
    if (!runId) {
      setGlobalError("Call Start first to get a run_id.");
      return false;
    }
    setStatus(key, "running");
    try {
      const data = key === "rag" ? await runRag(backendUrl, runId, question) : await STEP_API[key](backendUrl, runId);
      setResults((prev) => ({ ...prev, [key]: data }));
      setStatus(key, "done");
      return true;
    } catch (e) {
      setStatus(key, "error");
      const label = STEP_ORDER.find((s) => s.key === key)?.label || key;
      setGlobalError(`${label} Agent failed: ${e.message}`);
      return false;
    }
  };

  const runAllRemaining = async () => {
    setRunningAll(true);
    setGlobalError("");
    for (const step of STEP_ORDER) {
      const ok = await runStep(step.key);
      if (!ok) break;
    }
    setRunningAll(false);
  };

  const handleReset = async () => {
    try {
      await resetAll(backendUrl);
    } catch (e) {
      setGlobalError("Reset request failed: " + e.message);
    }
    setRunId(null);
    setStepStatus({});
    setResults({});
    setGlobalError("");
    setTopic("");
    setQuestion("");
  };

  const isRunning = (key) => stepStatus[key] === "running";

  return (
    <div className="app">
      <header>
        <h1>
          <span className="logo" /> Autonomous Research Scientist
        </h1>
        <nav className="tabs">
          <button className={view === "pipeline" ? "active" : ""} onClick={() => setView("pipeline")}>
            Pipeline
          </button>
          <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}>
            Chat
          </button>
          <button className={view === "history" ? "active" : ""} onClick={() => setView("history")}>
            Report History
          </button>
        </nav>
        <div className="conn">
          <input
            className="backend-input"
            type="text"
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
          />
          <span className={`dot ${connected ? "ok" : ""}`} />
          <span>{connected ? "connected" : "not reachable"}</span>
        </div>
      </header>

      <main>
        {view === "history" ? (
          <ReportHistory backendUrl={backendUrl} />
        ) : view === "chat" ? (
          <ChatPanel backendUrl={backendUrl} runId={runId} topic={topic} />
        ) : (
          <>
            <div className="card">
              <h2>1. Start a research query</h2>
              <div className="controls-row">
                <input
                  type="text"
                  placeholder="e.g. deep learning for industrial surface defect detection"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
                <button className="primary" onClick={handleStart}>
                  Start (Supervisor)
                </button>
                <button onClick={runAllRemaining} disabled={!runId || runningAll}>
                  {runningAll ? "Running..." : "Run all remaining steps"}
                </button>
                <button className="danger" onClick={handleReset}>
                  Reset everything
                </button>
              </div>

              {runId && (
                <div className="run-id-row">
                  Run ID: <span className="run-id-box">{runId}</span>
                  <span className="badge">{topic}</span>
                </div>
              )}

              {globalError && <div className="warnings">⚠ {globalError}</div>}
            </div>

            <div className="card">
              <h2>2. Pipeline progress</h2>
              <Stepper stepStatus={stepStatus} />
            </div>

            {results.literature !== undefined && (
              <LiteratureSection data={results.literature} onRun={() => runStep("literature")} running={isRunning("literature")} />
            )}
            {results.rag !== undefined && (
              <RagSection
                data={results.rag}
                question={question}
                onQuestionChange={setQuestion}
                onRun={() => runStep("rag")}
                running={isRunning("rag")}
              />
            )}
            {results.analysis !== undefined && (
              <AnalysisSection data={results.analysis} onRun={() => runStep("analysis")} running={isRunning("analysis")} />
            )}
            {results.gap !== undefined && (
              <GapSection data={results.gap} onRun={() => runStep("gap")} running={isRunning("gap")} />
            )}
            {results.hypothesis !== undefined && (
              <HypothesisSection data={results.hypothesis} onRun={() => runStep("hypothesis")} running={isRunning("hypothesis")} />
            )}
            {results.experiment !== undefined && (
              <ExperimentSection data={results.experiment} onRun={() => runStep("experiment")} running={isRunning("experiment")} />
            )}
            {results.verification !== undefined && (
              <VerificationSection data={results.verification} onRun={() => runStep("verification")} running={isRunning("verification")} />
            )}
            {results.report !== undefined && (
              <ReportSection
                data={results.report}
                runId={runId}
                backendUrl={backendUrl}
                onRun={() => runStep("report")}
                running={isRunning("report")}
              />
            )}

            {/* Manual controls to trigger any step (also works before its section has ever run) */}
            {runId && (
              <div className="card">
                <h2>3. Run any step manually</h2>
                <div className="controls-row">
                  {STEP_ORDER.map((s) => (
                    <button key={s.key} onClick={() => runStep(s.key)} disabled={isRunning(s.key)}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      <footer>Talks to your local FastAPI backend — nothing here is sent anywhere else.</footer>
    </div>
  );
}
