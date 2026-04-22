import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { uploadPhoto, analyzeStyle, compareOutfits } from "../services/api";
import AppHeader from "../components/AppHeader";
import HistoryPicker from "../components/HistoryPicker";
import ErrorBanner from "../components/ErrorBanner";
import "./Compare.css";

const OCCASIONS = ["", "Work", "Date night", "Casual", "Formal", "Weekend"];

function OutfitSlot({ label, slot, onFile, onPickFromHistory, onClear }) {
  const fileInputRef = useRef(null);

  return (
    <div className={`compare-slot ${slot.analysis ? "compare-slot--filled" : ""}`}>
      <div className="compare-slot-label">{label}</div>

      {slot.analysis ? (
        <div className="compare-slot-filled">
          {slot.analysis.image_url && (
            <img
              src={slot.analysis.image_url}
              alt={`Outfit ${label}`}
              className="compare-slot-img"
            />
          )}
          <div className="compare-slot-tags">
            {(slot.analysis.style_tags || []).slice(0, 4).map((t, i) => (
              <span key={i} className="style-tag">{t}</span>
            ))}
          </div>
          <p className="compare-slot-summary">
            {slot.analysis.summary?.slice(0, 120)}
            {slot.analysis.summary?.length > 120 ? "…" : ""}
          </p>
          <button className="btn-outline compare-slot-clear" onClick={onClear}>
            Clear
          </button>
        </div>
      ) : (
        <div className="compare-slot-empty">
          {slot.loading ? (
            <div className="loading-spinner">Analysing…</div>
          ) : (
            <>
              <input
                type="file"
                accept="image/*"
                ref={fileInputRef}
                style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
              />
              <button
                className="btn-primary"
                onClick={() => fileInputRef.current.click()}
              >
                Upload Photo
              </button>
              <button
                className="btn-secondary"
                onClick={onPickFromHistory}
              >
                Pick from History
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function Compare() {
  const { user, token } = useAuth();

  const emptySlot = () => ({ analysis: null, loading: false });
  const [slotA, setSlotA] = useState(emptySlot());
  const [slotB, setSlotB] = useState(emptySlot());
  const [occasion, setOccasion] = useState("");
  const [customOccasion, setCustomOccasion] = useState("");
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [pickerFor, setPickerFor] = useState(null); // "A" | "B" | null

  const effectiveOccasion = occasion === "__custom" ? customOccasion : occasion;

  async function handleFile(slot, setSlot, file) {
    setError("");
    setSlot((s) => ({ ...s, loading: true }));
    try {
      const { url } = await uploadPhoto(file, token);
      const analysis = await analyzeStyle(url, token);
      setSlot({ analysis: { ...analysis, image_url: url }, loading: false });
    } catch (err) {
      setError(err.message || "Upload/analysis failed.");
      setSlot(emptySlot());
    }
  }

  function handleHistorySelect(analysis) {
    if (pickerFor === "A") setSlotA({ analysis, loading: false });
    if (pickerFor === "B") setSlotB({ analysis, loading: false });
    setPickerFor(null);
  }

  async function handleCompare() {
    if (!slotA.analysis || !slotB.analysis) return;
    setError("");
    setComparing(true);
    setResult(null);
    try {
      const outfitA = slotA.analysis.id
        ? { analysis_id: slotA.analysis.id }
        : { image_url: slotA.analysis.image_url };
      const outfitB = slotB.analysis.id
        ? { analysis_id: slotB.analysis.id }
        : { image_url: slotB.analysis.image_url };
      const data = await compareOutfits(outfitA, outfitB, effectiveOccasion, token);
      setResult(data);
    } catch (err) {
      setError(err.message || "Comparison failed.");
    } finally {
      setComparing(false);
    }
  }

  function handleReset() {
    setSlotA(emptySlot());
    setSlotB(emptySlot());
    setOccasion("");
    setCustomOccasion("");
    setResult(null);
    setError("");
  }

  const canCompare = !!slotA.analysis && !!slotB.analysis && !comparing;

  return (
    <div className="compare-container">
      <AppHeader />
      <header className="home-header">
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/wardrobe" className="btn-secondary">Wardrobe</Link>
          <Link to="/looks" className="btn-secondary">Generate</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="compare-main">
        <h2 className="compare-heading">Outfit Compare</h2>

        {error && (
          <ErrorBanner
            message={error}
            context="SYS/COMPARE"
            onRetry={slotA.analysis && slotB.analysis ? handleCompare : undefined}
          />
        )}

        {result ? (
          <CompareResult
            result={result}
            onReset={handleReset}
          />
        ) : (
          <>
            <div className="compare-arena">
              <OutfitSlot
                label="A"
                slot={slotA}
                onFile={(f) => handleFile("A", setSlotA, f)}
                onPickFromHistory={() => setPickerFor("A")}
                onClear={() => setSlotA(emptySlot())}
              />

              <div className="compare-vs">VS</div>

              <OutfitSlot
                label="B"
                slot={slotB}
                onFile={(f) => handleFile("B", setSlotB, f)}
                onPickFromHistory={() => setPickerFor("B")}
                onClear={() => setSlotB(emptySlot())}
              />
            </div>

            <div className="compare-controls">
              <div className="compare-occasion-row">
                <label className="compare-occasion-label">OCCASION</label>
                <select
                  className="compare-occasion-select"
                  value={occasion}
                  onChange={(e) => setOccasion(e.target.value)}
                >
                  {OCCASIONS.map((o) => (
                    <option key={o} value={o}>
                      {o || "— any —"}
                    </option>
                  ))}
                  <option value="__custom">Custom…</option>
                </select>
                {occasion === "__custom" && (
                  <input
                    type="text"
                    className="compare-occasion-custom"
                    placeholder="e.g. Job interview"
                    value={customOccasion}
                    onChange={(e) => setCustomOccasion(e.target.value)}
                  />
                )}
              </div>

              <button
                className="btn-primary compare-submit"
                onClick={handleCompare}
                disabled={!canCompare}
              >
                {comparing ? "Comparing…" : "Compare →"}
              </button>
            </div>
          </>
        )}
      </main>

      {pickerFor && (
        <HistoryPicker
          onSelect={handleHistorySelect}
          onClose={() => setPickerFor(null)}
        />
      )}
    </div>
  );
}

function OutfitResultCard({ label, data, analysis, isWinner }) {
  return (
    <div className={`compare-result-card ${isWinner ? "compare-result-card--winner" : ""}`}>
      <div className="compare-result-card-label">{label}</div>
      {analysis?.image_url && (
        <img
          src={analysis.image_url}
          alt={`Outfit ${label}`}
          className="compare-result-img"
        />
      )}
      <div className="compare-result-best-for">
        <span className="compare-result-meta-label">BEST FOR</span>
        <span>{data?.best_for}</span>
      </div>
      <div className="compare-result-section">
        <span className="compare-result-meta-label">STRENGTHS</span>
        <ul className="compare-result-list">
          {(data?.strengths || []).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      {(data?.concerns || []).length > 0 && (
        <div className="compare-result-section">
          <span className="compare-result-meta-label">CONCERNS</span>
          <ul className="compare-result-list compare-result-list--concerns">
            {data.concerns.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function CompareResult({ result, onReset }) {
  const { comparison, outfit_a, outfit_b } = result;
  const verdict = comparison?.verdict;
  const verdictLabel =
    verdict === "TIE"
      ? "TIE"
      : verdict === "A"
      ? "Outfit A wins"
      : "Outfit B wins";

  return (
    <div className="compare-result">
      <div
        className={`compare-verdict compare-verdict--${(verdict || "tie").toLowerCase()}`}
      >
        <span className="compare-verdict-badge">VERDICT</span>
        <span className="compare-verdict-label">{verdictLabel}</span>
        <p className="compare-verdict-reason">{comparison?.verdict_reason}</p>
      </div>

      <div className="compare-result-grid">
        <OutfitResultCard
          label="A"
          data={comparison?.outfit_a}
          analysis={outfit_a}
          isWinner={verdict === "A"}
        />
        <OutfitResultCard
          label="B"
          data={comparison?.outfit_b}
          analysis={outfit_b}
          isWinner={verdict === "B"}
        />
      </div>

      {comparison?.contextual_notes && (
        <div className="compare-notes">
          <span className="compare-result-meta-label">CONTEXT</span>
          <p>{comparison.contextual_notes}</p>
        </div>
      )}

      <button className="btn-secondary compare-reset" onClick={onReset}>
        ← Start Over
      </button>
    </div>
  );
}
