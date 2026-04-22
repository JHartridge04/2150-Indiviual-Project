import { useState, useEffect } from "react";
import "./LoadingMessage.css";

export default function LoadingMessage({ messages, intervalMs = 2300, prefix }) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % messages.length), intervalMs);
    return () => clearInterval(t);
  }, [messages.length, intervalMs]);

  return (
    <span className="ns-loading-msg">
      {prefix && <span className="ns-loading-msg-prefix">{prefix} </span>}
      <span className="ns-loading-msg-text">{messages[idx]}</span>
      <span className="ns-loading-msg-cursor">▌</span>
    </span>
  );
}
