import { useState } from "react";

export function Collapsible({ summary, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="collapsible">
      <button type="button" className="collapse-toggle" onClick={() => setOpen((o) => !o)}>
        <span className={`chevron ${open ? "open" : ""}`}>▸</span>
        {open ? "Hide details" : "Show details"}
        {summary ? ` — ${summary}` : ""}
      </button>
      {open && <div className="collapse-body">{children}</div>}
    </div>
  );
}

export function Chips({ items }) {
  if (!items || items.length === 0) {
    return <span className="empty-note">none</span>;
  }
  return (
    <>
      {items.map((item, i) => (
        <span className="chip" key={i}>
          {item}
        </span>
      ))}
    </>
  );
}

export function VerdictBadge({ verdict }) {
  const v = (verdict || "unsupported").toLowerCase();
  return <span className={`verdict ${v}`}>{verdict || "unsupported"}</span>;
}

export function Warnings({ errors }) {
  if (!errors || errors.length === 0) return null;
  return (
    <div className="warnings">
      {errors.map((e, i) => (
        <div key={i}>⚠ {e}</div>
      ))}
    </div>
  );
}

export function EmptyNote({ children }) {
  return <div className="empty-note-block">{children}</div>;
}

export function FieldLabel({ children }) {
  return <span className="field-label">{children}</span>;
}
