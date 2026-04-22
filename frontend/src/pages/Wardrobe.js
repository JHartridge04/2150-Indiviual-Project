/**
 * Wardrobe.js
 * Upload clothing photos, auto-tag them with AI, manage your wardrobe,
 * derive your style profile, and build outfits around anchor items.
 */

import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AppHeader from "../components/AppHeader";
import {
  uploadWardrobeItems,
  getWardrobe,
  deleteWardrobeItem,
  updateWardrobeItem,
  deriveStyleFromWardrobe,
  applyDerivedStyle,
  buildOutfit,
  runStyleAudit,
} from "../services/api";
import WardrobeCard from "../components/WardrobeCard";
import WardrobeEditModal from "../components/WardrobeEditModal";
import OutfitResultModal from "../components/OutfitResultModal";
import StyleAuditModal from "../components/StyleAuditModal";
import ErrorBanner from "../components/ErrorBanner";
import "./Wardrobe.css";

const FILTERS = ["all", "owned", "wishlist"];

const WARDROBE_FEATURES = [
  "Auto-tagged with AI on upload",
  "Build outfits around any piece",
  "Get wardrobe gap audits",
  "Derive your core style profile",
];

function EmptyWardrobeState({ onUploadClick }) {
  return (
    <div className="wardrobe-empty">
      <div className="wardrobe-empty-sys">
        <span className="wardrobe-empty-sys-accent">SYS/WRDRB</span>
        <span className="wardrobe-empty-sys-sep">›</span>
        <span>0 ITEMS</span>
      </div>
      <div className="wardrobe-empty-top">
        <div className="wardrobe-empty-text">
          <h3 className="wardrobe-empty-headline">
            Wardrobe<br />Is Empty
          </h3>
          <p className="wardrobe-empty-body">
            Your wardrobe is the engine of No Stylist. Add clothing items and
            unlock outfit building, gap analysis, and AI-derived style profiles.
          </p>
        </div>
        <div className="wardrobe-empty-hatch" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div
              key={i}
              className="wardrobe-empty-tick"
              style={{ top: `${i * 13 + 5}%`, width: i % 4 === 0 ? 10 : 6 }}
            />
          ))}
        </div>
      </div>
      <button className="wardrobe-empty-cta" onClick={onUploadClick}>
        <span className="wardrobe-empty-cta-dot" />
        Upload items →
      </button>
      <div className="wardrobe-empty-rule">
        <div className="wardrobe-empty-rule-line" />
        <span className="wardrobe-empty-rule-label">unlock with 1+ items</span>
        <div className="wardrobe-empty-rule-line" />
      </div>
      <div className="wardrobe-empty-features">
        {WARDROBE_FEATURES.map((f, i) => (
          <div key={i} className="wardrobe-empty-feature">
            <div className="wardrobe-empty-feature-box">
              <div className="wardrobe-empty-feature-dot" />
            </div>
            <span className="wardrobe-empty-feature-label">{f}</span>
          </div>
        ))}
      </div>
      <div className="wardrobe-empty-stamp">
        <div className="wardrobe-empty-stamp-line" />
        <span className="wardrobe-empty-stamp-ref">REF:WRDRB-000</span>
      </div>
    </div>
  );
}

export default function Wardrobe() {
  const { user, token } = useAuth();

  // Items
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  // Upload
  const [uploadFiles, setUploadFiles] = useState([]);
  const [uploadOwnership, setUploadOwnership] = useState("owned");
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null); // { text, type }

  // Edit modal
  const [editItem, setEditItem] = useState(null);

  // Derive style
  const [derivingStyle, setDerivingStyle] = useState(false);
  const [derivedStyle, setDerivedStyle] = useState(null);
  const [deriveInsufficient, setDeriveInsufficient] = useState(false);
  const [applyingStyle, setApplyingStyle] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);

  // Outfit builder (anchor-based)
  const [buildingOutfit, setBuildingOutfit] = useState(false);
  const [outfitResult, setOutfitResult] = useState(null);
  const [outfitAnchorItem, setOutfitAnchorItem] = useState(null);
  const [buildError, setBuildError] = useState("");

  // Style audit
  const [auditOpen, setAuditOpen] = useState(false);
  const [runningAudit, setRunningAudit] = useState(false);
  const [auditResult, setAuditResult] = useState(null);
  const [auditError, setAuditError] = useState("");

  // ---------------------------------------------------------------------------
  // Load items
  // ---------------------------------------------------------------------------
  const loadItems = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const ownership = filter !== "all" ? filter : undefined;
      const data = await getWardrobe(token, ownership);
      setItems(data.items || []);
    } catch (err) {
      setError(err.message || "Failed to load wardrobe.");
    } finally {
      setLoading(false);
    }
  }, [token, filter]);

  useEffect(() => { loadItems(); }, [loadItems]);

  // ---------------------------------------------------------------------------
  // Upload
  // ---------------------------------------------------------------------------
  function handleFileChange(e) {
    const selected = Array.from(e.target.files || []).filter(
      (f) => f.type.startsWith("image/") && f.size <= 10 * 1024 * 1024
    );
    setUploadFiles(selected);
    setUploadMsg(null);
  }

  async function handleUpload(e) {
    e.preventDefault();
    if (!uploadFiles.length) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const data = await uploadWardrobeItems(uploadFiles, uploadOwnership, token);
      const successCount = data.items?.length || 0;
      const failCount = data.failures?.length || 0;
      if (successCount > 0) {
        setUploadMsg({
          text: `${successCount} item${successCount > 1 ? "s" : ""} uploaded${failCount ? `, ${failCount} failed` : ""}.`,
          type: "success",
        });
        setUploadFiles([]);
        e.target.reset();
        await loadItems();
      } else {
        setUploadMsg({ text: `All ${failCount} uploads failed.`, type: "error" });
      }
    } catch (err) {
      setUploadMsg({ text: err.message || "Upload failed.", type: "error" });
    } finally {
      setUploading(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Delete / edit
  // ---------------------------------------------------------------------------
  async function handleDelete(id) {
    try {
      await deleteWardrobeItem(id, token);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      setError(err.message || "Failed to delete item.");
    }
  }

  async function handleSaveEdit(itemId, updates) {
    const data = await updateWardrobeItem(itemId, updates, token);
    setItems((prev) => prev.map((i) => (i.id === itemId ? data.item : i)));
    setEditItem(null);
  }

  // ---------------------------------------------------------------------------
  // Derive style
  // ---------------------------------------------------------------------------
  async function handleDeriveStyle() {
    setDerivingStyle(true);
    setError("");
    try {
      const data = await deriveStyleFromWardrobe(token);
      setDerivedStyle(data);
      setApplySuccess(false);
    } catch (err) {
      if (err.message?.toLowerCase().includes("at least 5 items")) {
        setDeriveInsufficient(true);
      } else {
        setError(err.message || "Failed to derive style.");
      }
    } finally {
      setDerivingStyle(false);
    }
  }

  async function handleApplyStyle() {
    if (!derivedStyle) return;
    setApplyingStyle(true);
    try {
      await applyDerivedStyle({ preferred_styles: derivedStyle.preferred_styles }, token);
      setApplySuccess(true);
    } catch (err) {
      setError(err.message || "Failed to apply style.");
    } finally {
      setApplyingStyle(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Outfit builder (anchor-based)
  // ---------------------------------------------------------------------------
  async function handleBuildOutfitAround(item) {
    setEditItem(null);
    setOutfitAnchorItem(item);
    setOutfitResult(null);
    setBuildError("");
    setBuildingOutfit(true);
    try {
      const data = await buildOutfit(item.id, "", token);
      setOutfitResult(data);
    } catch (err) {
      setBuildError(err.message || "Failed to build outfit.");
    } finally {
      setBuildingOutfit(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Style audit
  // ---------------------------------------------------------------------------
  async function handleRunAudit() {
    setAuditOpen(true);
    setAuditResult(null);
    setAuditError("");
    setRunningAudit(true);
    try {
      const data = await runStyleAudit(token);
      setAuditResult(data);
    } catch (err) {
      setAuditError(err.message || "Audit failed.");
    } finally {
      setRunningAudit(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="wardrobe-container">
      <AppHeader />
      <header className="home-header">
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/compare" className="btn-secondary">Compare</Link>
          <Link to="/looks" className="btn-secondary">Generate</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="wardrobe-main">
        <h2 className="wardrobe-heading">My Wardrobe</h2>
        <p className="wardrobe-subtitle">
          Upload your clothing items — AI auto-tags each one. Edit any item and
          use "Build Outfit Around This" to create a complete look.
        </p>

        {error && <ErrorBanner message={error} context="SYS/WRDRB" />}

        {/* ---- Upload section ---- */}
        <section className="wardrobe-upload-card" id="wardrobe-upload-card">
          <h3 className="card-title">Add Items</h3>
          <form onSubmit={handleUpload} className="wardrobe-upload-form">
            <label className="wardrobe-file-zone">
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
              <span className="wardrobe-file-icon">📂</span>
              {uploadFiles.length > 0 ? (
                <span>{uploadFiles.length} file{uploadFiles.length > 1 ? "s" : ""} selected</span>
              ) : (
                <span>Click to choose photos (multiple allowed)</span>
              )}
            </label>

            <div className="wardrobe-ownership-row">
              <span className="we-field-label">These items are:</span>
              {["owned", "wishlist"].map((o) => (
                <label key={o} className="wardrobe-radio-label">
                  <input
                    type="radio"
                    name="uploadOwnership"
                    value={o}
                    checked={uploadOwnership === o}
                    onChange={() => setUploadOwnership(o)}
                  />
                  {o === "owned" ? "Owned" : "Wishlist"}
                </label>
              ))}
            </div>

            {uploadMsg && uploadMsg.type === "success" && (
              <p className="wardrobe-upload-msg wardrobe-upload-msg--success">
                {uploadMsg.text}
              </p>
            )}
            {uploadMsg && uploadMsg.type === "error" && (
              <ErrorBanner message={uploadMsg.text} context="SYS/WRDRB" />
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={!uploadFiles.length || uploading}
            >
              {uploading ? "Uploading & tagging…" : "Upload Items"}
            </button>
          </form>
        </section>

        {/* ---- Toolbar ---- */}
        <div className="wardrobe-toolbar">
          <div className="wardrobe-filters">
            {FILTERS.map((f) => (
              <button
                key={f}
                className={`wardrobe-filter-btn${filter === f ? " wardrobe-filter-btn--active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <button
            className="btn-secondary"
            onClick={handleDeriveStyle}
            disabled={derivingStyle}
          >
            {derivingStyle ? "Analysing…" : "✨ Derive My Style"}
          </button>

          <button
            className="btn-secondary"
            onClick={handleRunAudit}
          >
            Run Style Audit
          </button>
        </div>

        {/* ---- Item grid ---- */}
        {loading ? (
          <div className="loading-spinner">Loading wardrobe…</div>
        ) : items.length === 0 ? (
          filter !== "all" ? (
            <p className="no-items">No {filter} items yet.</p>
          ) : (
            <EmptyWardrobeState
              onUploadClick={() =>
                document.getElementById("wardrobe-upload-card")?.scrollIntoView({ behavior: "smooth" })
              }
            />
          )
        ) : (
          <div className="wardrobe-grid">
            {items.map((item) => (
              <WardrobeCard
                key={item.id}
                item={item}
                onClick={() => setEditItem(item)}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      {/* ---- Derive insufficient-items gate ---- */}
      {deriveInsufficient && (
        <div
          className="wardrobe-modal-overlay"
          onClick={() => setDeriveInsufficient(false)}
        >
          <div className="wardrobe-modal wardrobe-derive-gate" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="we-close"
              onClick={() => setDeriveInsufficient(false)}
              aria-label="Close"
            >
              ×
            </button>
            <div className="wdg-sys">
              <span className="wdg-sys-accent">SYS/DERIVE</span>
              <span className="wdg-sys-sep">›</span>
              <span>MIN_ITEMS=5</span>
            </div>
            <h3 className="wdg-headline">Not Enough<br />Data</h3>
            <p className="wdg-body">
              Add at least <strong>5 wardrobe items</strong> before deriving your
              style profile — more items produce more accurate results.
            </p>
            <div className="wdg-counter">
              <div className="wdg-counter-label">ITEMS PRESENT</div>
              <div className="wdg-blocks">
                [{"▓".repeat(Math.min(items.length, 5))}{"░".repeat(Math.max(0, 5 - items.length))}]
              </div>
              <div className="wdg-counts">
                <span className="wdg-count-item">
                  CURRENT <span className="wdg-count-val wdg-count-val--accent">{items.length}</span>
                </span>
                <span className="wdg-count-item">
                  NEEDED <span className="wdg-count-val">5</span>
                </span>
              </div>
              <div className="wdg-track">
                <div className="wdg-fill" style={{ width: `${Math.min(items.length / 5, 1) * 100}%` }} />
              </div>
              <div className="wdg-remaining">
                {Math.max(0, 5 - items.length)} MORE ITEM{5 - items.length !== 1 ? "S" : ""} TO UNLOCK
              </div>
            </div>
            <button
              className="wdg-cta"
              onClick={() => {
                setDeriveInsufficient(false);
                document.getElementById("wardrobe-upload-card")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              <span className="wdg-cta-dot" />
              Upload items →
            </button>
          </div>
        </div>
      )}

      {/* ---- Derived style modal ---- */}
      {derivedStyle && (
        <div
          className="wardrobe-modal-overlay"
          onClick={() => { setDerivedStyle(null); setApplySuccess(false); }}
        >
          <div className="wardrobe-modal" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="we-close"
              onClick={() => { setDerivedStyle(null); setApplySuccess(false); }}
              aria-label="Close"
            >
              ×
            </button>
            <h3 className="card-title">Your Derived Style</h3>

            {derivedStyle.style_summary && (
              <p className="derive-summary">{derivedStyle.style_summary}</p>
            )}

            {derivedStyle.preferred_styles?.length > 0 && (
              <div className="derive-section">
                <strong>Preferred Styles</strong>
                <div className="derive-chips">
                  {derivedStyle.preferred_styles.map((s, i) => (
                    <span key={i} className="chip">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {derivedStyle.color_palette?.length > 0 && (
              <div className="derive-section">
                <strong>Colour Palette</strong>
                <div className="derive-chips">
                  {derivedStyle.color_palette.map((c, i) => (
                    <span key={i} className="wardrobe-color-chip">{c}</span>
                  ))}
                </div>
              </div>
            )}

            {applySuccess ? (
              <p className="derive-applied">✓ Applied to your profile!</p>
            ) : (
              <button
                className="btn-primary derive-apply-btn"
                onClick={handleApplyStyle}
                disabled={applyingStyle}
              >
                {applyingStyle ? "Applying…" : "Apply to My Profile"}
              </button>
            )}
          </div>
        </div>
      )}

      {/* ---- Edit modal ---- */}
      {editItem && (
        <WardrobeEditModal
          item={editItem}
          onSave={handleSaveEdit}
          onDelete={handleDelete}
          onBuildOutfit={handleBuildOutfitAround}
          onClose={() => setEditItem(null)}
        />
      )}

      {/* ---- Outfit result modal ---- */}
      {(buildingOutfit || outfitResult || buildError) && outfitAnchorItem && (
        <OutfitResultModal
          loading={buildingOutfit}
          anchorItem={outfitAnchorItem}
          wardrobeItems={items}
          result={outfitResult}
          error={buildError}
          onRetry={() => handleBuildOutfitAround(outfitAnchorItem)}
          onClose={() => { setOutfitResult(null); setOutfitAnchorItem(null); setBuildError(""); }}
        />
      )}

      {/* ---- Style audit modal ---- */}
      {auditOpen && (
        <StyleAuditModal
          audit={auditResult}
          runningAudit={runningAudit}
          auditError={auditError}
          itemCount={items.length}
          onRetry={handleRunAudit}
          onClose={() => setAuditOpen(false)}
        />
      )}
    </div>
  );
}
