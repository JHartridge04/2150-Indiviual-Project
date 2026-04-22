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
import Skeleton from "../components/Skeleton";
import ProgressBar from "../components/ProgressBar";
import ErrorBanner from "../components/ErrorBanner";
import "./Recommendations.css";

const REC_MSGS = [
  "READING STYLE PROFILE...",
  "SCANNING PRODUCT CATALOGUE...",
  "MATCHING TO YOUR AESTHETIC...",
  "RANKING BY RELEVANCE...",
  "FINALISING OUTPUT...",
];

function RecCardSkeleton() {
  return (
    <div className="rec-card">
      <Skeleton height={200} />
      <div className="rec-card-skel-body">
        <Skeleton width="55%" height={7} />
        <Skeleton width="88%" height={9} />
        <Skeleton width="68%" height={7} />
        <div className="rec-card-skel-footer">
          <Skeleton width="32%" height={11} />
          <Skeleton width="30%" height={22} />
        </div>
      </div>
    </div>
  );
}

function RecommendationsSkeleton() {
  return (
    <div className="rec-skel-wrap">
      <ProgressBar messages={REC_MSGS} intervalMs={2300} prefix="SYS/RECS >" />
      <div className="rec-grid rec-grid--skel">
        <RecCardSkeleton />
        <RecCardSkeleton />
        <RecCardSkeleton />
        <RecCardSkeleton />
      </div>
    </div>
  );
}

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
          <Link to="/compare" className="btn-secondary">Compare</Link>
          <Link to="/looks" className="btn-secondary">Generate</Link>
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

        {error && <ErrorBanner message={error} context="SYS/RECS" onRetry={handleRefresh} />}

        {loading ? (
          <RecommendationsSkeleton />
        ) : items.length === 0 ? (
          <p className="no-items">No recommendations found.</p>
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
