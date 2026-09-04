import { useState } from "react";
import { mdToHtml } from "../markdown.js";
import { Collapsible, Warnings } from "./Common.jsx";
import { downloadReportPdf } from "../api.js";

export default function ReportSection({ data, runId, backendUrl, onRun, running }) {
  const reportText = data?.report || "";
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const handleDownloadMd = () => {
    const blob = new Blob([reportText], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research_report_${runId || "output"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async () => {
    setPdfError("");
    setDownloadingPdf(true);
    try {
      const blob = await downloadReportPdf(backendUrl, runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research_report_${runId || "output"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setPdfError("PDF download failed: " + e.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="card section">
      <div className="section-header">
        <h2>📄 Final Report</h2>
        <button onClick={onRun} disabled={running}>
          {running ? "Running..." : "Run Report Agent"}
        </button>
      </div>

      {reportText ? (
        <Collapsible summary="final report" defaultOpen>
          <div className="report-body" dangerouslySetInnerHTML={{ __html: mdToHtml(reportText) }} />
          <div className="report-actions">
            <button onClick={handleDownloadMd}>Download report.md</button>
            <button className="primary" onClick={handleDownloadPdf} disabled={downloadingPdf}>
              {downloadingPdf ? "Preparing PDF..." : "Download report.pdf"}
            </button>
          </div>
          {pdfError && <div className="warnings">⚠ {pdfError}</div>}
        </Collapsible>
      ) : (
        data && <div className="empty-note-block">No report generated yet.</div>
      )}

      <Warnings errors={data?.errors} />
    </div>
  );
}
