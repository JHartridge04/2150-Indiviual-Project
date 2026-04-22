/**
 * History.js
 * Shows the authenticated user's past AI style analyses as a clickable grid.
 * Clicking a card expands an inline detail panel beneath the grid with the
 * analysis summary and all associated tags.
 */

import React, { useState, useEffect, useCallback } from "react";
import AppHeader from "../components/AppHeader";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getHistory, deleteHistoryItem } from "../services/api";
import OutfitCard from "../components/OutfitCard";
import ErrorBanner from "../components/ErrorBanner";
import "./History.css";

function EmptyHistoryState() {
  return (
    <div className="history-empty">
      <div className="history-empty-sys">
        <span className="history-empty-sys-accent">SYS/HIST</span>
        <span className="history-empty-sys-sep">›</span>
        <span>EMPTY_STATE</span>
      </div>
      <h3 className="history-empty-headline">
        No Analyses<br />Yet
      </h3>
      <p className="history-empty-body">
        Every outfit you upload gets analysed and stored here. Compare looks
        over time, revisit your style evolution, and pull up past results to
        generate new recommendations.
      </p>
      <Link to="/" className="history-empty-cta">
        <span className="history-empty-cta-dot" />
        Upload your first outfit →
      </Link>
      <div className="history-empty-rule">
        <div className="history-empty-rule-line" />
        <span className="history-empty-rule-label">your analyses will appear below</span>
        <div className="history-empty-rule-line" />
      </div>
      <div className="history-ghost-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="history-ghost-card" style={{ opacity: 0.5 + i * 0.04 }}>
            <div className="history-ghost-img">
              <div className="history-ghost-crossh history-ghost-crossh-h" />
              <div className="history-ghost-crossh history-ghost-crossh-v" />
              <span className="history-ghost-label">outfit photo</span>
            </div>
            <div className="history-ghost-meta">
              <div className="history-ghost-line" style={{ width: "55%" }} />
              <div className="history-ghost-line" style={{ width: "80%", opacity: 0.6 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function History() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  // ---------------------------------------------------------------------------
  // Fetch history on mount
  // ---------------------------------------------------------------------------
  const fetchHistory = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const data = await getHistory(token);
      setAnalyses(data.analyses || []);
    } catch (err) {
      setError(err.message || "Failed to load history.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  // ---------------------------------------------------------------------------
  // Card selection — clicking the same card again collapses the panel
  // ---------------------------------------------------------------------------
  function handleCardClick(analysis) {
    setSelected((prev) => (prev?.id === analysis.id ? null : analysis));
  }

  // ---------------------------------------------------------------------------
  // Delete handler
  // ---------------------------------------------------------------------------
  async function handleDelete(id) {
    try {
      await deleteHistoryItem(id, token);
      setAnalyses((prev) => prev.filter((a) => a.id !== id));
      setSelected((prev) => (prev?.id === id ? null : prev));
    } catch (err) {
      setError(err.message || "Failed to delete analysis.");
    }
  }

  function formatDate(isoString) {
    return new Date(isoString).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  // Merge all tag types for the detail panel
  const allTags = selected
    ? [
        ...(selected.colors || []),
        ...(selected.silhouettes || []),
        ...(selected.style_tags || []),
      ]
    : [];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="history-container">
      <AppHeader />
      <header className="home-header">
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/wardrobe" className="btn-secondary">Wardrobe</Link>
          <Link to="/compare" className="btn-secondary">Compare</Link>
          <Link to="/looks" className="btn-secondary">Generate</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/logout" className="btn-outline">
            Sign Out
          </Link>
        </nav>
      </header>

      <main className="history-main">
        <h2 className="history-heading">Style History</h2>

        {error && <ErrorBanner message={error} context="SYS/HIST" onRetry={fetchHistory} />}

        {loading ? (
          <div className="loading-spinner">Loading history…</div>
        ) : analyses.length === 0 ? (
          <EmptyHistoryState />
        ) : (
          <>
            <div className="history-grid">
              {analyses.map((analysis) => (
                <OutfitCard
                  key={analysis.id}
                  analysis={analysis}
                  isSelected={selected?.id === analysis.id}
                  onClick={() => handleCardClick(analysis)}
                  onDelete={handleDelete}
                />
              ))}
            </div>

            {selected && (
              <div className="history-detail">
                <h3 className="history-detail-title">Style Summary</h3>
                <p className="history-detail-date">{formatDate(selected.created_at)}</p>
                {selected.summary && (
                  <p className="history-detail-summary">{selected.summary}</p>
                )}
                {allTags.length > 0 && (
                  <div className="tag-list">
                    {allTags.map((tag, i) => (
                      <span key={i} className="style-tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                <div className="history-detail-actions">
                  <button
                    className="btn-primary"
                    onClick={() => navigate(`/recommendations/${selected.id}`)}
                  >
                    Get Recommendations →
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
