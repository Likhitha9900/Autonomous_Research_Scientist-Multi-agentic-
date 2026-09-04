import { Chips, Collapsible, FieldLabel, Warnings } from "./Common.jsx";

export default function HypothesisSection({ data, onRun, running }) {
  const hyps = data?.hypotheses || [];
  const total = data?.total_hypotheses ?? hyps.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>💡 Hypothesis Agent — research questions</h2>
        <div className="section-header-right">
          <span className="badge">{total} hypotheses</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Hypothesis Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${total} hypotheses`}>
          {hyps.length === 0 && (
            <div className="empty-note-block">
              No hypotheses generated — check that the Gap step produced gaps first.
            </div>
          )}

          {hyps.map((h, i) => (
            <div className="item" key={i}>
              <h3>{h.research_question}</h3>
              <p>
                <strong>Hypothesis:</strong> {h.hypothesis}
              </p>
              <FieldLabel>Addresses gap</FieldLabel>
              <p>{h.gap}</p>
              <FieldLabel>Supporting papers</FieldLabel>
              <div>
                <Chips items={h.supporting_paper_ids} />
              </div>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
