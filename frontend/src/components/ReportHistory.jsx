import { useEffect, useState } from "react";
import { listReports, getReport, deleteReports, downloadReportPdf } from "../api.js";
import { mdToHtml } from "../markdown.js";

export default function ReportHistory({ backendUrl }) {
  const [reports, setReports] = useState([]);
  const [selected, setSelected] = useState(null); // full record
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listReports(backendUrl);
      setReports(data.reports || []);
    } catch (e) {
      setError("Could not load report history: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendUrl]);

  const openReport = async (runId) => {
    setError("");
    try {
      const data = await getReport(backendUrl, runId);
      setSelected(data);
    } catch (e) {
      setError("Could not load that report: " + e.message);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Permanently delete the entire report history? This cannot be undone.")) {
      return;
    }
    try {
      await deleteReports(backendUrl);
      setSelected(null);
      refresh();
    } catch (e) {
      setError("Could not clear history: " + e.message);
    }
  };

  const handleDownloadPdf = async (runId) => {
    setError("");
    setDownloadingPdf(true);
    try {
      const blob = await downloadReportPdf(backendUrl, runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research_report_${runId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError("PDF download failed: " + e.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="card">
      <div className="section-header">
        <h2>🗂 Report History</h2>
        <div className="section-header-right">
          <button onClick={refresh} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
          <button className="danger" onClick={handleDeleteAll} disabled={reports.length === 0}>
            Delete all history
          </button>
        </div>
      </div>

      {error && <div className="warnings">⚠ {error}</div>}

      {reports.length === 0 && !loading && (
        <div className="empty-note-block">
          No reports saved yet — every report you generate on the Pipeline tab is stored here
          automatically, and stays saved even after restarting the backend.
        </div>
      )}

      <div className="history-list">
        {reports.map((r) => (
          <div
            className={`history-item ${selected?.run_id === r.run_id ? "selected" : ""}`}
            key={r.run_id}
            onClick={() => openReport(r.run_id)}
          >
            <div className="history-topic">{r.topic}</div>
            {r.question && <div className="history-question">Q: {r.question}</div>}
            <div className="history-meta">
              <code>{r.run_id}</code> · {new Date(r.saved_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div className="item" style={{ marginTop: 16 }}>
          <div className="meta">
            Run <code>{selected.run_id}</code> · saved {new Date(selected.saved_at).toLocaleString()}
          </div>
          <div className="report-body" dangerouslySetInnerHTML={{ __html: mdToHtml(selected.report) }} />
          <div className="report-actions">
            <button
              className="primary"
              onClick={() => handleDownloadPdf(selected.run_id)}
              disabled={downloadingPdf}
            >
              {downloadingPdf ? "Preparing PDF..." : "Download report.pdf"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
