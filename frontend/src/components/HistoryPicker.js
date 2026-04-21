import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { getHistory } from "../services/api";
import "./HistoryPicker.css";

export default function HistoryPicker({ onSelect, onClose }) {
  const { token } = useAuth();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getHistory(token);
        setAnalyses(data.analyses || []);
      } catch (err) {
        setError(err.message || "Failed to load history.");
      } finally {
        setLoading(false);
      }
    }
    if (token) load();
  }, [token]);

  return (
    <div className="history-picker-overlay" onClick={onClose}>
      <div
        className="history-picker-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="history-picker-header">
          <span className="history-picker-title">SELECT FROM HISTORY</span>
          <button className="history-picker-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="loading-spinner">Loading…</div>
        ) : analyses.length === 0 ? (
          <p className="history-picker-empty">No analyses yet.</p>
        ) : (
          <div className="history-picker-grid">
            {analyses.map((a) => (
              <button
                key={a.id}
                className="history-picker-item"
                onClick={() => onSelect(a)}
              >
                {a.image_url ? (
                  <img
                    src={a.image_url}
                    alt="outfit"
                    className="history-picker-thumb"
                    loading="lazy"
                  />
                ) : (
                  <div className="history-picker-no-img">NO IMG</div>
                )}
                <span className="history-picker-date">
                  {new Date(a.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
