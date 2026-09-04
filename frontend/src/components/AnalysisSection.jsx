import { Chips, Collapsible, FieldLabel, Warnings } from "./Common.jsx";

export default function AnalysisSection({ data, onRun, running }) {
  const analyses = data?.analyses || [];
  const total = data?.total_analyses ?? analyses.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>🔍 Paper Analysis Agent — structured extraction</h2>
        <div className="section-header-right">
          <span className="badge">{total} analyzed</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Analysis Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${total} analyzed`}>
          {analyses.length === 0 && (
            <div className="empty-note-block">
              No analyses produced — check that Literature and RAG Retrieve found relevant papers first.
            </div>
          )}

          {analyses.map((a) => (
            <div className="item" key={a.paper_id}>
              <h3>{a.title}</h3>
              <div className="meta">
                <code>{a.paper_id}</code>
              </div>
              <FieldLabel>Methods</FieldLabel>
              <div>
                <Chips items={a.methods} />
              </div>
              <FieldLabel>Datasets</FieldLabel>
              <div>
                <Chips items={a.datasets} />
              </div>
              <FieldLabel>Metrics</FieldLabel>
              <div>
                <Chips items={a.metrics} />
              </div>
              <FieldLabel>Results</FieldLabel>
              <p>{a.results || "unknown"}</p>
              <FieldLabel>Limitations</FieldLabel>
              <div>
                <Chips items={a.limitations} />
              </div>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
