// Small, dependency-free markdown renderer - just enough for the report
// format the Report Agent produces (headers, bold, inline code, lists,
// paragraphs). Not a general-purpose markdown parser.

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(text) {
  let out = escapeHtml(text);
  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/`(.+?)`/g, "<code>$1</code>");
  return out;
}

export function mdToHtml(md) {
  if (!md) return "";
  const lines = md.split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const line of lines) {
    if (/^### /.test(line)) {
      closeList();
      html += `<h3>${inline(line.slice(4))}</h3>`;
      continue;
    }
    if (/^## /.test(line)) {
      closeList();
      html += `<h2>${inline(line.slice(3))}</h2>`;
      continue;
    }
    if (/^# /.test(line)) {
      closeList();
      html += `<h1>${inline(line.slice(2))}</h1>`;
      continue;
    }
    if (/^- /.test(line)) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inline(line.slice(2))}</li>`;
      continue;
    }
    closeList();
    if (line.trim() === "") continue;
    html += `<p>${inline(line)}</p>`;
  }
  closeList();
  return html;
}
