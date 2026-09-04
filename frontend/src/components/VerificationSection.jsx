import { Collapsible, VerdictBadge, Warnings } from "./Common.jsx";

export default function VerificationSection({ data, onRun, running }) {
  const verification = data?.verification || {};
  const results = verification.results || [];
  const checked = verification.checked ?? results.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>✅ Verification Agent — evidence checks</h2>
        <div className="section-header-right">
          <span className="badge">{checked} checked</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Verification Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${checked} checked`}>
          {results.length === 0 && (
            <div className="empty-note-block">
              Nothing to verify — check that the Gap step produced gaps first.
            </div>
          )}

          {results.map((r, i) => (
            <div className="item" key={i}>
              <h3>{r.gap}</h3>
              <VerdictBadge verdict={r.verdict} />
              <p>{r.reasoning}</p>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
