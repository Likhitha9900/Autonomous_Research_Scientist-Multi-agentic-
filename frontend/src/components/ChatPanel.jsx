import { useEffect, useRef, useState } from "react";
import { sendChatMessage, getChatHistory } from "../api.js";

export default function ChatPanel({ backendUrl, runId, topic }) {
  const [messages, setMessages] = useState([]); // {question, answer, saved_at}
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!runId) {
      setMessages([]);
      return;
    }
    setLoadingHistory(true);
    setError("");
    getChatHistory(backendUrl, runId)
      .then((data) => setMessages(data.history || []))
      .catch(() => {
        /* no saved history yet for this run - fine */
      })
      .finally(() => setLoadingHistory(false));
  }, [backendUrl, runId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || !runId || sending) return;
    setSending(true);
    setError("");
    setInput("");
    setMessages((prev) => [...prev, { question, answer: null, saved_at: null }]);
    try {
      const data = await sendChatMessage(backendUrl, runId, question);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = data;
        return next;
      });
    } catch (e) {
      setError("Chat failed: " + e.message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!runId) {
    return (
      <div className="card chat-panel">
        <h2>💬 Ask about this research</h2>
        <div className="empty-note-block">
          Start a research query on the Pipeline tab first, then come back here to ask questions
          about whatever the agents have collected so far.
        </div>
      </div>
    );
  }

  return (
    <div className="card chat-panel">
      <div className="section-header">
        <h2>💬 Ask about this research</h2>
        {topic && <span className="badge">{topic}</span>}
      </div>
      <p className="hint">
        Ask anything about the papers, gaps, hypotheses, experiments, or report collected so far
        for this run. Every answer is saved and reloads automatically.
      </p>

      <div className="chat-messages">
        {loadingHistory && <div className="empty-note-block">Loading saved chat history...</div>}
        {!loadingHistory && messages.length === 0 && (
          <div className="empty-note-block">No questions asked yet for this run.</div>
        )}

        {messages.map((m, i) => (
          <div className="chat-exchange" key={i}>
            <div className="chat-bubble chat-user">{m.question}</div>
            <div className="chat-bubble chat-bot">
              {m.answer === null ? <span className="chat-typing">Thinking…</span> : m.answer}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="warnings">⚠ {error}</div>}

      <div className="controls-row chat-input-row">
        <input
          type="text"
          placeholder="e.g. which papers support the second gap?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
        />
        <button className="primary" onClick={handleSend} disabled={sending || !input.trim()}>
          {sending ? "Asking..." : "Ask"}
        </button>
      </div>
    </div>
  );
}
