// Thin wrapper around every backend endpoint. Every function takes the
// backend base URL explicitly (rather than a module-level constant) so the
// user can point this at a different host/port from the UI without a rebuild.

async function request(baseUrl, method, path, body) {
  const res = await fetch(baseUrl.replace(/\/$/, "") + path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try {
    data = await res.json();
  } catch {
    // no JSON body (e.g. some error responses) - leave data as {}
  }
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const checkHealth = (baseUrl) => request(baseUrl, "GET", "/");

export const startRun = (baseUrl, topic) => request(baseUrl, "POST", "/start", { topic });

export const runLiterature = (baseUrl, runId) =>
  request(baseUrl, "POST", `/run/literature/${runId}`);

export const runRag = (baseUrl, runId, question) =>
  request(baseUrl, "POST", `/run/rag/${runId}`, { question: question || null });

export const runAnalysis = (baseUrl, runId) =>
  request(baseUrl, "POST", `/run/analysis/${runId}`);

export const runGap = (baseUrl, runId) => request(baseUrl, "POST", `/run/gap/${runId}`);

export const runHypothesis = (baseUrl, runId) =>
  request(baseUrl, "POST", `/run/hypothesis/${runId}`);

export const runExperiment = (baseUrl, runId) =>
  request(baseUrl, "POST", `/run/experiment/${runId}`);

export const runVerification = (baseUrl, runId) =>
  request(baseUrl, "POST", `/run/verification/${runId}`);

export const runReport = (baseUrl, runId) => request(baseUrl, "POST", `/run/report/${runId}`);

export const getState = (baseUrl, runId) => request(baseUrl, "GET", `/state/${runId}`);

export const resetAll = (baseUrl) => request(baseUrl, "POST", "/reset");

export const listReports = (baseUrl) => request(baseUrl, "GET", "/reports");

export const getReport = (baseUrl, runId) => request(baseUrl, "GET", `/reports/${runId}`);

export const deleteReports = (baseUrl) => request(baseUrl, "DELETE", "/reports");

export async function downloadReportPdf(baseUrl, runId) {
  const res = await fetch(baseUrl.replace(/\/$/, "") + `/reports/${runId}/pdf`);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && data.detail) detail = data.detail;
    } catch {
      // no JSON body - keep default detail
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.blob();
}

export const sendChatMessage = (baseUrl, runId, question) =>
  request(baseUrl, "POST", `/chat/${runId}`, { question });

export const getChatHistory = (baseUrl, runId) => request(baseUrl, "GET", `/chat/${runId}`);

export const clearChatHistory = (baseUrl, runId) => request(baseUrl, "DELETE", `/chat/${runId}`);
