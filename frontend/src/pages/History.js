/**
 * History.js
 * Shows the authenticated user's past AI style analyses as a clickable grid.
 * Clicking a card expands an inline detail panel beneath the grid with the
 * analysis summary and all associated tags.
 */

import React, { useState, useEffect } from "react";
import AppHeader from "../components/AppHeader";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getHistory, deleteHistoryItem } from "../services/api";
import OutfitCard from "../components/OutfitCard";
import "./History.css";

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
  useEffect(() => {
    async function fetchHistory() {
      try {
        const data = await getHistory(token);
        setAnalyses(data.analyses || []);
      } catch (err) {
        setError(err.message || "Failed to load history.");
      } finally {
        setLoading(false);
      }
    }

    if (token) fetchHistory();
  }, [token]);

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

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="loading-spinner">Loading history…</div>
        ) : analyses.length === 0 ? (
          <p className="no-items">
            No analyses yet.{" "}
            <Link to="/">Upload an outfit</Link> to get started.
          </p>
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
