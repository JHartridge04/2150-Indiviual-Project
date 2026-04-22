import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { fillGap } from "../services/api";
import RecommendationCard from "./RecommendationCard";
import Skeleton from "./Skeleton";
import ProgressBar from "./ProgressBar";
import ErrorBanner from "./ErrorBanner";
import "./StyleAuditModal.css";

const AUDIT_MSGS = [
  "LOADING WARDROBE DATA...",
  "IDENTIFYING STYLE CLUSTERS...",
  "CHECKING COLOUR COHESION...",
  "RUNNING GAP ANALYSIS...",
  "GENERATING AUDIT REPORT...",
];

function AuditGate({ itemCount, onClose }) {
  const NEEDED = 5;
  const filled = Math.min(itemCount, NEEDED);
  const blocks = "▓".repeat(filled) + "░".repeat(NEEDED - filled);

  return (
    <div className="sam-gate">
      <div className="sam-gate-sys">
        <span className="sam-gate-sys-accent">SYS/AUDIT</span>
        <span className="sam-gate-sys-sep">›</span>
        <span>MIN_ITEMS=5</span>
      </div>
      <h3 className="sam-gate-headline">
        Not Enough<br />Signal
      </h3>
      <p className="sam-gate-body">
        Add at least <strong>5 wardrobe items</strong> for the style audit to
        identify meaningful gaps in your wardrobe.
      </p>
      <div className="sam-gate-counter">
        <div className="sam-gate-counter-label">ITEMS REQUIRED</div>
        <div className="sam-gate-blocks">[{blocks}]</div>
        <div className="sam-gate-counts">
          <span className="sam-gate-count-item">
            CURRENT <span className="sam-gate-count-val sam-gate-count-val--accent">{filled}</span>
          </span>
          <span className="sam-gate-count-item">
            NEEDED <span className="sam-gate-count-val">{NEEDED}</span>
          </span>
        </div>
        <div className="sam-gate-track">
          <div className="sam-gate-fill" style={{ width: `${(filled / NEEDED) * 100}%` }} />
        </div>
        <div className="sam-gate-remaining">
          {NEEDED - filled} MORE ITEM{NEEDED - filled !== 1 ? "S" : ""} TO UNLOCK AUDIT
        </div>
      </div>
      <Link to="/wardrobe" className="sam-gate-cta" onClick={onClose}>
        <span className="sam-gate-cta-dot" />
        Add wardrobe items →
      </Link>
      <div className="sam-gate-footer">
        <span className="sam-gate-footer-ref">REF:AUDIT-GATE-001</span>
        <span className="sam-gate-footer-ver">SYS/01 • v1.0</span>
      </div>
    </div>
  );
}

function AuditSkeleton() {
  return (
    <div className="sam-skel-wrap">
      <div className="sam-skel-header">
        <span className="sam-skel-title">STYLE AUDIT</span>
        <span className="sam-skel-version">SYS/01 • v1.0</span>
      </div>

      <div className="sam-skel-section">
        <div className="sam-skel-label">OVERALL SCORE</div>
        <div className="sam-skel-score-row">
          <Skeleton width={52} height={52} style={{ flexShrink: 0 }} />
          <div className="sam-skel-score-lines">
            <Skeleton width="65%" height={8} />
            <Skeleton width="88%" height={7} />
            <Skeleton width="50%" height={7} />
          </div>
        </div>
      </div>

      <div className="sam-skel-section">
        <div className="sam-skel-label">KEY FINDINGS</div>
        {[0, 1, 2].map((i) => (
          <div key={i} className="sam-skel-finding-row">
            <Skeleton
              width={14}
              height={14}
              style={i === 0
                ? { background: "var(--ns-accent)", opacity: 0.4, flexShrink: 0 }
                : { flexShrink: 0 }}
            />
            <div className="sam-skel-finding-lines">
              <Skeleton width="72%" height={8} />
              <Skeleton width="92%" height={7} />
            </div>
          </div>
        ))}
      </div>

      <div className="sam-skel-section">
        <div className="sam-skel-label">STYLE CLUSTERS DETECTED</div>
        <div className="sam-skel-chips">
          {[68, 52, 80, 60, 44, 72].map((w, i) => (
            <Skeleton
              key={i}
              width={w}
              height={19}
              style={i < 2 ? { background: "var(--ns-accent)", opacity: 0.2 } : {}}
            />
          ))}
        </div>
      </div>

      <div className="sam-skel-section">
        <div className="sam-skel-label">CATEGORY COVERAGE</div>
        {[["TOPS", 78], ["BOTTOMS", 55], ["OUTERWEAR", 32], ["FOOTWEAR", 60]].map(([label, val]) => (
          <div key={label} className="sam-skel-coverage-row">
            <span className="sam-skel-coverage-label">{label}</span>
            <div className="sam-skel-coverage-track">
              <div className="sam-skel-coverage-fill" style={{ width: `${val}%` }} />
            </div>
          </div>
        ))}
      </div>

      <div className="sam-skel-progress">
        <ProgressBar messages={AUDIT_MSGS} intervalMs={2500} prefix="SYS/AUDIT >" />
      </div>
    </div>
  );
}

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

      {error && <ErrorBanner message={error} context="SYS/GAP" onRetry={handleFindPieces} />}

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

export default function StyleAuditModal({ audit, runningAudit, auditError, itemCount = 0, onRetry, onClose }) {
  const timestamp = useState(() => formatTimestamp())[0];

  return (
    <div className="sam-overlay" onClick={onClose}>
      <div className="sam-modal" onClick={(e) => e.stopPropagation()}>
        <button className="sam-close" onClick={onClose} aria-label="Close">×</button>

        {runningAudit ? (
          <AuditSkeleton />
        ) : auditError ? (
          auditError.toLowerCase().includes("at least 5 items") ? (
            <AuditGate itemCount={itemCount} onClose={onClose} />
          ) : (
            <div className="sam-error-state">
              <ErrorBanner message={auditError} context="SYS/AUDIT" onRetry={onRetry} />
            </div>
          )
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
