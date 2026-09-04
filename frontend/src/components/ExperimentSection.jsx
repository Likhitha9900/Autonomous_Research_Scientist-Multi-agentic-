import { Chips, Collapsible, FieldLabel, Warnings } from "./Common.jsx";

export default function ExperimentSection({ data, onRun, running }) {
  const exps = data?.experiments || [];
  const total = data?.total_experiments ?? exps.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>🧪 Experiment Agent — experiment plans</h2>
        <div className="section-header-right">
          <span className="badge">{total} plans</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Experiment Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${total} plans`}>
          {exps.length === 0 && (
            <div className="empty-note-block">
              No experiment plans generated — check that the Hypothesis step ran first.
            </div>
          )}

          {exps.map((e, i) => (
            <div className="item" key={i}>
              <h3>{e.hypothesis}</h3>
              <FieldLabel>Baselines</FieldLabel>
              <div>
                <Chips items={e.baselines} />
              </div>
              <FieldLabel>Datasets</FieldLabel>
              <div>
                <Chips items={e.datasets} />
              </div>
              <FieldLabel>Metrics</FieldLabel>
              <div>
                <Chips items={e.metrics} />
              </div>
              <FieldLabel>Plan</FieldLabel>
              <p>{e.experiment_plan}</p>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
