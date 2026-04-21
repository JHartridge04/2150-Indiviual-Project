import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fillGap } from "../services/api";
import RecommendationCard from "./RecommendationCard";
import "./StyleAuditModal.css";

function formatTimestamp() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  return `${y}.${m}.${d} ${hh}:${mm}`;
}

function GapCard({ gap }) {
  const { token } = useAuth();
  const [products, setProducts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleFindPieces() {
    setLoading(true);
    setError("");
    try {
      const data = await fillGap(
        {
          gap_title: gap.title,
          gap_description: gap.description,
          suggested_search: gap.suggested_search,
        },
        token
      );
      setProducts(data.products || []);
    } catch (err) {
      setError(err.message || "Failed to find products.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="sam-gap-card">
      <div className="sam-gap-header">
        <span className="sam-gap-title">{gap.title}</span>
      </div>
      <p className="sam-gap-desc">{gap.description}</p>

      {error && <div className="error-banner sam-gap-error">{error}</div>}

      {products === null ? (
        <button
          className="btn-outline sam-find-btn"
          onClick={handleFindPieces}
          disabled={loading}
        >
          {loading ? "Finding pieces…" : "Find pieces for this gap →"}
        </button>
      ) : products.length === 0 ? (
        <p className="sam-no-products">No products found for this search.</p>
      ) : (
        <div className="sam-products-grid">
          {products.map((p, i) => (
            <RecommendationCard key={i} item={p} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function StyleAuditModal({ audit, runningAudit, auditError, onClose }) {
  const timestamp = useState(() => formatTimestamp())[0];

  return (
    <div className="sam-overlay" onClick={onClose}>
      <div className="sam-modal" onClick={(e) => e.stopPropagation()}>
        <button className="sam-close" onClick={onClose} aria-label="Close">×</button>

        {runningAudit ? (
          <div className="sam-loading">
            <div className="loading-spinner">Running audit…</div>
            <p className="sam-loading-hint">Analysing your wardrobe with AI — this takes a few seconds.</p>
          </div>
        ) : auditError ? (
          <div className="sam-error-state">
            {auditError.includes("5 items") ? (
              <p className="sam-too-few">
                {auditError}{" "}
                <Link to="/wardrobe" onClick={onClose}>Add items →</Link>
              </p>
            ) : (
              <div className="error-banner">{auditError}</div>
            )}
          </div>
        ) : audit ? (
          <>
            <div className="sam-stamp">
              <span className="sam-stamp-label">AUDIT.RESULT</span>
              <span className="sam-stamp-date">{timestamp}</span>
            </div>

            {audit.summary && (
              <p className="sam-summary">{audit.summary}</p>
            )}

            {audit.strengths?.length > 0 && (
              <div className="sam-section">
                <h4 className="sam-section-title">STRENGTHS</h4>
                <ul className="sam-strengths">
                  {audit.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {audit.gaps?.length > 0 && (
              <div className="sam-section">
                <h4 className="sam-section-title">GAPS — {audit.gaps.length} IDENTIFIED</h4>
                <div className="sam-gaps">
                  {audit.gaps.map((gap) => (
                    <GapCard key={gap.id} gap={gap} />
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
