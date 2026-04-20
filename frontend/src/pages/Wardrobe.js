/**
 * Wardrobe.js
 * Upload clothing photos, auto-tag them with AI, manage your wardrobe,
 * derive your style profile, and build outfits around anchor items.
 */

import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  uploadWardrobeItems,
  getWardrobe,
  deleteWardrobeItem,
  updateWardrobeItem,
  deriveStyleFromWardrobe,
  applyDerivedStyle,
  buildOutfit,
} from "../services/api";
import WardrobeCard from "../components/WardrobeCard";
import WardrobeEditModal from "../components/WardrobeEditModal";
import OutfitResultModal from "../components/OutfitResultModal";
import "./Wardrobe.css";

const FILTERS = ["all", "owned", "wishlist"];

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
  const [applyingStyle, setApplyingStyle] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);

  // Outfit builder (anchor-based)
  const [buildingOutfit, setBuildingOutfit] = useState(false);
  const [outfitResult, setOutfitResult] = useState(null);
  const [outfitAnchorItem, setOutfitAnchorItem] = useState(null);

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
      setError(err.message || "Failed to derive style.");
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
    setEditItem(null); // close edit modal first
    setBuildingOutfit(true);
    setError("");
    try {
      const data = await buildOutfit(item.id, "", token);
      setOutfitAnchorItem(item);
      setOutfitResult(data);
    } catch (err) {
      setError(err.message || "Failed to build outfit.");
    } finally {
      setBuildingOutfit(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="wardrobe-container">
      <header className="home-header">
        <h1 className="app-title">👗 Style Assistant</h1>
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/profile" className="btn-secondary">Profile</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="wardrobe-main">
        <h2 className="wardrobe-heading">My Wardrobe</h2>
        <p className="wardrobe-subtitle">
          Upload your clothing items — AI auto-tags each one. Edit any item and
          use "Build Outfit Around This" to create a complete look.
        </p>

        {error && <div className="error-banner">{error}</div>}

        {/* ---- Upload section ---- */}
        <section className="wardrobe-upload-card">
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

            {uploadMsg && (
              <p className={`wardrobe-upload-msg wardrobe-upload-msg--${uploadMsg.type}`}>
                {uploadMsg.text}
              </p>
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
        </div>

        {/* Building outfit indicator */}
        {buildingOutfit && (
          <div className="loading-spinner">Building outfit with AI…</div>
        )}

        {/* ---- Item grid ---- */}
        {loading ? (
          <div className="loading-spinner">Loading wardrobe…</div>
        ) : items.length === 0 ? (
          <p className="no-items">
            {filter !== "all"
              ? `No ${filter} items yet.`
              : "No items yet — upload some clothing photos to get started!"}
          </p>
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
      {outfitResult && outfitAnchorItem && (
        <OutfitResultModal
          anchorItem={outfitAnchorItem}
          wardrobeItems={items}
          result={outfitResult}
          onClose={() => { setOutfitResult(null); setOutfitAnchorItem(null); }}
        />
      )}
    </div>
  );
}
