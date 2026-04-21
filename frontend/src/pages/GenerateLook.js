import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { generateLook } from "../services/api";
import AppHeader from "../components/AppHeader";
import RecommendationCard from "../components/RecommendationCard";
import "./GenerateLook.css";

const OCCASIONS = ["Work", "Date night", "Casual weekend", "Formal", "Night out", "Travel", "Other"];
const WEATHER_OPTIONS = ["Cold", "Warm", "Hot", "Rainy", "Mild"];
const VIBE_CHIPS = ["Minimalist", "Bold", "Streetwear", "Preppy", "Retro", "Monochrome"];

function formatTimestamp() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  return `${y}.${m}.${d} ${hh}:${mm}`;
}

export default function GenerateLook() {
  const { user, token } = useAuth();

  const [occasion, setOccasion] = useState("");
  const [occasionCustom, setOccasionCustom] = useState("");
  const [weather, setWeather] = useState("");
  const [vibe, setVibe] = useState("");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [generatedAt, setGeneratedAt] = useState("");
  const [error, setError] = useState("");

  const effectiveOccasion = occasion === "Other" ? occasionCustom : occasion;

  async function handleGenerate() {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const data = await generateLook(
        {
          occasion: effectiveOccasion,
          weather,
          vibe,
          notes,
        },
        token
      );
      setResult(data);
      setGeneratedAt(formatTimestamp());
    } catch (err) {
      setError(err.message || "Failed to generate look.");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setError("");
  }

  return (
    <div className="gl-container">
      <AppHeader />
      <header className="home-header">
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/wardrobe" className="btn-secondary">Wardrobe</Link>
          <Link to="/compare" className="btn-secondary">Compare</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="gl-main">
        <h2 className="gl-heading">Generate a Look</h2>

        {error && <div className="error-banner">{error}</div>}

        {result ? (
          <LookResult
            result={result}
            generatedAt={generatedAt}
            onReset={handleReset}
          />
        ) : (
          <LookForm
            occasion={occasion}
            setOccasion={setOccasion}
            occasionCustom={occasionCustom}
            setOccasionCustom={setOccasionCustom}
            weather={weather}
            setWeather={setWeather}
            vibe={vibe}
            setVibe={setVibe}
            notes={notes}
            setNotes={setNotes}
            loading={loading}
            onGenerate={handleGenerate}
          />
        )}
      </main>
    </div>
  );
}

function LookForm({
  occasion, setOccasion, occasionCustom, setOccasionCustom,
  weather, setWeather, vibe, setVibe, notes, setNotes,
  loading, onGenerate,
}) {
  return (
    <div className="gl-form">
      {/* Occasion */}
      <div className="gl-field-group">
        <label className="gl-field-label">OCCASION</label>
        <select
          className="gl-select"
          value={occasion}
          onChange={(e) => setOccasion(e.target.value)}
        >
          <option value="">— any —</option>
          {OCCASIONS.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
        {occasion === "Other" && (
          <input
            type="text"
            className="gl-input"
            placeholder="Describe the occasion…"
            value={occasionCustom}
            onChange={(e) => setOccasionCustom(e.target.value)}
          />
        )}
      </div>

      {/* Weather */}
      <div className="gl-field-group">
        <label className="gl-field-label">WEATHER</label>
        <div className="gl-pills">
          {WEATHER_OPTIONS.map((w) => (
            <button
              key={w}
              type="button"
              className={`gl-pill${weather === w ? " gl-pill--active" : ""}`}
              onClick={() => setWeather((prev) => (prev === w ? "" : w))}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {/* Vibe */}
      <div className="gl-field-group">
        <label className="gl-field-label">VIBE</label>
        <input
          type="text"
          className="gl-input"
          placeholder="e.g. minimalist, bold, laid-back…"
          value={vibe}
          onChange={(e) => setVibe(e.target.value)}
        />
        <div className="gl-chips">
          {VIBE_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className="gl-chip"
              onClick={() => setVibe(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div className="gl-field-group">
        <label className="gl-field-label">ADDITIONAL NOTES</label>
        <textarea
          className="gl-textarea"
          placeholder="Anything else? e.g. 'I want to look effortless', 'no heels', 'keep it monochrome'…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      <button
        className="btn-primary gl-submit"
        onClick={onGenerate}
        disabled={loading}
      >
        {loading ? "Designing your look…" : "Generate Look →"}
      </button>

      {loading && (
        <p className="gl-loading-hint">
          Scanning your wardrobe and sourcing products — this takes 10–15 seconds.
        </p>
      )}
    </div>
  );
}

function LookResult({ result, generatedAt, onReset }) {
  const wardrobeById = Object.fromEntries(
    (result.wardrobe_items || []).map((item) => [item.id, item])
  );

  return (
    <div className="gl-result">
      {/* Header stamp */}
      <div className="gl-result-stamp">
        <span className="gl-stamp-label">LOOK.GENERATED</span>
        <span className="gl-stamp-date">{generatedAt}</span>
      </div>

      {/* Title + summary */}
      <div className="gl-result-header">
        <h3 className="gl-result-title">{result.title}</h3>
        {result.summary && (
          <p className="gl-result-summary">{result.summary}</p>
        )}
      </div>

      {/* Wardrobe pieces */}
      {result.wardrobe_pieces?.length > 0 && (
        <div className="gl-result-section">
          <h4 className="gl-section-title">YOUR WARDROBE</h4>
          <div className="gl-pieces-grid">
            {result.wardrobe_pieces.map((piece, i) => {
              const item = wardrobeById[piece.item_id];
              return (
                <div key={i} className="gl-piece-card">
                  {item?.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.description || piece.role}
                      className="gl-piece-img"
                      loading="lazy"
                    />
                  ) : (
                    <div className="gl-piece-no-img">NO IMG</div>
                  )}
                  <div className="gl-piece-info">
                    <span className="gl-role-chip">{piece.role}</span>
                    <p className="gl-piece-reason">{piece.reason}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Missing pieces */}
      {result.missing_pieces?.length > 0 && (
        <div className="gl-result-section">
          <h4 className="gl-section-title">WHAT'S MISSING</h4>
          <ul className="gl-missing-list">
            {result.missing_pieces.map((piece, i) => (
              <li key={i} className="gl-missing-item">
                <div className="gl-missing-header">
                  <span className="gl-role-chip">{piece.role}</span>
                  <span className="gl-missing-desc">{piece.description}</span>
                </div>
                {piece.products?.length > 0 && (
                  <div className="gl-missing-products">
                    {piece.products.map((product, j) => (
                      <RecommendationCard key={j} item={product} />
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button className="btn-secondary gl-reset" onClick={onReset}>
        ← Generate Another
      </button>
    </div>
  );
}
