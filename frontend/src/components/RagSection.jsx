import { Collapsible, Warnings } from "./Common.jsx";

export default function RagSection({ data, question, onQuestionChange, onRun, running }) {
  const retrieved = data?.retrieved_context || [];

  return (
    <div className="card section">
      <div className="section-header">
        <h2>🎯 RAG Retrieve Agent — narrows down which papers get analyzed</h2>
        <div className="section-header-right">
          {data && (
            <span className="badge">
              {data.total_relevant_papers ?? 0} papers · {data.total_retrieved_passages ?? 0} passages
            </span>
          )}
        </div>
      </div>

      <p className="hint">
        Optional: ask a specific question to focus the rest of the pipeline on. If you leave this
        blank, it falls back to your original topic and just acts as a general relevance filter.
      </p>
      <div className="controls-row">
        <input
          type="text"
          placeholder="e.g. how well do current models generalize across hospitals?"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
        />
        <button onClick={onRun} disabled={running}>
          {running ? "Running..." : "Run RAG Retrieve Agent"}
        </button>
      </div>

      {data && (
        <div className="meta" style={{ marginTop: 12 }}>
          Question used: <em>{data.question || "(none - used topic)"}</em>
        </div>
      )}

      {data && (
        <Collapsible summary={`${retrieved.length} passages`}>
          {retrieved.length === 0 && (
            <div className="empty-note-block">No relevant passages retrieved.</div>
          )}

          {retrieved.map((c, i) => (
            <div className="item" key={i}>
              <div className="meta">
                <code>{c.paper_id}</code> — {c.title}
              </div>
              <p>{c.content}</p>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
