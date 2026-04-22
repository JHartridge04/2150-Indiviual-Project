import { useState, useEffect } from "react";
import "./ProgressBar.css";

function useProgress(messages, intervalMs) {
  const [idx, setIdx] = useState(0);
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % messages.length), intervalMs);
    return () => clearInterval(t);
  }, [messages.length, intervalMs]);

  useEffect(() => {
    setPct(0);
    const step = intervalMs / 60;
    const inc = 100 / 60;
    const t = setInterval(() => setPct((p) => Math.min(p + inc, 100)), step);
    return () => clearInterval(t);
  }, [idx, intervalMs]);

  return { msg: messages[idx], pct };
}

export default function ProgressBar({ messages, intervalMs = 2300, prefix = "SYS >" }) {
  const { msg, pct } = useProgress(messages, intervalMs);
  const filled = Math.floor(pct / 10);
  const blocks = "[ " + "█".repeat(filled) + "░".repeat(10 - filled) + " ]";

  return (
    <div className="ns-progress-bar">
      <div className="ns-progress-msg-row">
        <span className="ns-progress-prefix">{prefix}</span>
        <span className="ns-progress-msg">{msg}</span>
        <span className="ns-progress-cursor">▌</span>
      </div>
      <div className="ns-progress-track">
        <div className="ns-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="ns-progress-footer">
        <span>{blocks}</span>
        <span>{Math.round(pct)}%</span>
      </div>
    </div>
  );
}
