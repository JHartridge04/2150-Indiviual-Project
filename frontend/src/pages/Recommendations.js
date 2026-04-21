/**
 * Recommendations.js
 * Displays AI-powered product recommendations for a specific style analysis.
 * Route: /recommendations/:analysisId
 */

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { useAuth } from "../context/AuthContext";
import { getRecommendations, refreshRecommendations } from "../services/api";
import RecommendationCard from "../components/RecommendationCard";
import "./Recommendations.css";

export default function Recommendations() {
  const { token, user } = useAuth();
  const { analysisId } = useParams();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token || !analysisId) return;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getRecommendations(analysisId, token);
        setItems(data.recommendations || []);
      } catch (err) {
        setError(err.message || "Failed to load recommendations.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token, analysisId]);

  async function handleRefresh() {
    if (!analysisId) return;
    setRefreshing(true);
    setError("");
    try {
      const data = await refreshRecommendations(analysisId, token);
      setItems(data.recommendations || []);
    } catch (err) {
      setError(err.message || "Failed to refresh recommendations.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="rec-container">
      <AppHeader />
      <header className="home-header">
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/wardrobe" className="btn-secondary">Wardrobe</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="rec-main">
        <div className="rec-header-row">
          <h2>Recommendations For You</h2>
          <button
            className="btn-secondary"
            onClick={handleRefresh}
            disabled={loading || refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <div className="loading-spinner">
            <p>Loading recommendations…</p>
            <p className="loading-hint">This may take a few seconds while AI selects products for you.</p>
          </div>
        ) : items.length === 0 ? (
          <p className="no-items">
            No recommendations found.{" "}
            <button className="link-btn" onClick={handleRefresh} disabled={refreshing}>
              Try again
            </button>
          </p>
        ) : (
          <div className="rec-grid">
            {items.map((item, idx) => (
              <RecommendationCard key={item.product_id || idx} item={item} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
