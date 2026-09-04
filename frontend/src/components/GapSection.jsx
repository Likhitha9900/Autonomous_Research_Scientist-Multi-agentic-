import { Chips, Collapsible, FieldLabel, Warnings } from "./Common.jsx";

export default function GapSection({ data, onRun, running }) {
  const gaps = data?.gaps || [];
  const total = data?.total_gaps ?? gaps.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>🧩 Research Gap Agent — identified gaps</h2>
        <div className="section-header-right">
          <span className="badge">{total} gaps</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Gap Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${total} gaps`}>
          {gaps.length === 0 && (
            <div className="empty-note-block">
              No gaps identified — check that the Analysis step produced results first.
            </div>
          )}

          {gaps.map((g, i) => (
            <div className="item" key={i}>
              <h3>{g.gap}</h3>
              <p>{g.evidence}</p>
              <FieldLabel>Supporting papers</FieldLabel>
              <div>
                <Chips items={g.supporting_paper_ids} />
              </div>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
