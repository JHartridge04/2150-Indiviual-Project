/**
 * Recommendations.js
 * Displays clothing recommendations sourced from the Flask backend.
 * Style tags are read from router state (passed by the Home page after
 * analysis) or from localStorage if the user navigates here directly.
 */

import React, { useEffect, useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getRecommendations } from "../services/api";
import RecommendationCard from "../components/RecommendationCard";
import "./Recommendations.css";

export default function Recommendations() {
  const { token, user } = useAuth();
  const location = useLocation();

  // Style tags may be passed as router state from the Home page
  const passedTags = location.state?.styleTags || [];

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // -------------------------------------------------------------------------
  // Load recommendations whenever tags change
  // -------------------------------------------------------------------------
  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getRecommendations(passedTags, token);
        setItems(data.recommendations || []);
      } catch (err) {
        setError(err.message || "Failed to load recommendations.");
      } finally {
        setLoading(false);
      }
    }

    if (token) load();
  // passedTags falls back to [] if no state is passed, but the stable source
  // of truth is location.state?.styleTags — use that as the dependency to
  // avoid a new array reference on every render triggering an infinite loop.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, location.state?.styleTags]);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="rec-container">
      {/* Header */}
      <header className="home-header">
        <h1 className="app-title">👗 Style Assistant</h1>
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">
            Upload
          </Link>
          <Link to="/logout" className="btn-outline">
            Sign Out
          </Link>
        </nav>
      </header>

      <main className="rec-main">
        <div className="rec-header-row">
          <h2>Recommendations For You</h2>
          {passedTags.length > 0 && (
            <div className="tag-list">
              {passedTags.map((t) => (
                <span key={t} className="style-tag">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="loading-spinner">Loading recommendations…</div>
        ) : items.length === 0 ? (
          <p className="no-items">No recommendations found. Try uploading an outfit first.</p>
        ) : (
          <div className="rec-grid">
            {items.map((item, idx) => (
              <RecommendationCard key={idx} item={item} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
