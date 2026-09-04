export const STEP_ORDER = [
  { key: "literature", label: "Literature" },
  { key: "rag", label: "RAG Retrieve" },
  { key: "analysis", label: "Analysis" },
  { key: "gap", label: "Gap" },
  { key: "hypothesis", label: "Hypothesis" },
  { key: "experiment", label: "Experiment" },
  { key: "verification", label: "Verification" },
  { key: "report", label: "Report" },
];

// Supervisor (the /start call) is shown as step 0, the rest follow the
// backend's actual pipeline order: Literature -> RAG Retrieve -> Analysis
// -> Gap -> Hypothesis -> Experiment -> Verification -> Report.
export default function Stepper({ stepStatus }) {
  const all = [{ key: "start", label: "Supervisor" }, ...STEP_ORDER];
  return (
    <div className="stepper">
      {all.map((s, i) => {
        const status = stepStatus[s.key] || "pending";
        return (
          <div className={`step ${status}`} key={s.key}>
            <div className="num">{i + 1}</div>
            <div className="label">{s.label}</div>
          </div>
        );
      })}
    </div>
  );
}
