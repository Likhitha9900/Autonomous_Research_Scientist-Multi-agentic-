import { Collapsible, Warnings } from "./Common.jsx";

export default function LiteratureSection({ data, onRun, running }) {
  const papers = data?.papers || [];
  const total = data?.total_papers ?? papers.length;

  return (
    <div className="card section">
      <div className="section-header">
        <h2>📚 Literature Agent — papers found</h2>
        <div className="section-header-right">
          <span className="badge">{total} papers</span>
          <button onClick={onRun} disabled={running}>
            {running ? "Running..." : "Run Literature Agent"}
          </button>
        </div>
      </div>

      {data && (
        <Collapsible summary={`${total} papers`}>
          {papers.length === 0 && (
            <div className="empty-note-block">No papers were found for this topic.</div>
          )}

          {papers.map((p) => (
            <div className="item" key={p.paper_id}>
              <h3>
                <a href={p.url} target="_blank" rel="noopener noreferrer">
                  {p.title}
                </a>
              </h3>
              <div className="meta">
                {(p.authors || []).join(", ")} · {p.year ?? "n.d."} · {p.source} · <code>{p.paper_id}</code>
              </div>
              <p>{p.abstract}</p>
              <span className="badge">{p.pdf_downloaded ? "PDF ingested" : "abstract only"}</span>
            </div>
          ))}
        </Collapsible>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
