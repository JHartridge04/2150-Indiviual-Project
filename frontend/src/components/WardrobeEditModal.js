import React, { useState } from "react";
import "./WardrobeEditModal.css";

const CATEGORIES = ["top", "bottom", "shoes", "outerwear", "accessory"];

function ChipInput({ label, values, onChange, placeholder }) {
  const [input, setInput] = useState("");

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = input.trim();
      if (trimmed && !values.includes(trimmed)) {
        onChange([...values, trimmed]);
      }
      setInput("");
    }
  }

  return (
    <div className="we-field-group">
      <label className="we-field-label">{label}</label>
      <div className="we-chip-wrap">
        {values.map((v) => (
          <span key={v} className="we-chip">
            {v}
            <button
              type="button"
              className="we-chip-remove"
              aria-label={`Remove ${v}`}
              onClick={() => onChange(values.filter((x) => x !== v))}
            >
              ×
            </button>
          </span>
        ))}
        <input
          className="we-chip-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Type and press Enter"}
        />
      </div>
    </div>
  );
}

export default function WardrobeEditModal({ item, onSave, onDelete, onBuildOutfit, onClose }) {
  const [form, setForm] = useState({
    category: item.category || "",
    ownership: item.ownership || "owned",
    colors: item.colors || [],
    style_tags: item.style_tags || [],
    description: item.description || "",
    user_notes: item.user_notes || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function setField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(item.id, form);
    } catch (err) {
      setError(err.message || "Failed to save.");
      setSaving(false);
    }
  }

  function handleDelete() {
    if (window.confirm("Delete this item permanently?")) {
      onDelete(item.id);
      onClose();
    }
  }

  return (
    <div className="we-overlay" onClick={onClose}>
      <div className="we-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="we-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        {item.image_url && (
          <img src={item.image_url} alt="Item preview" className="we-preview" />
        )}

        <form onSubmit={handleSave} className="we-form">
          <div className="we-row">
            <div className="we-field-group">
              <label className="we-field-label" htmlFor="we-category">Category</label>
              <select
                id="we-category"
                className="we-field-input"
                value={form.category}
                onChange={(e) => setField("category", e.target.value)}
              >
                <option value="">Select…</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="we-field-group">
              <label className="we-field-label" htmlFor="we-ownership">Ownership</label>
              <select
                id="we-ownership"
                className="we-field-input"
                value={form.ownership}
                onChange={(e) => setField("ownership", e.target.value)}
              >
                <option value="owned">Owned</option>
                <option value="wishlist">Wishlist</option>
              </select>
            </div>
          </div>

          <ChipInput
            label="Colors"
            values={form.colors}
            onChange={(v) => setField("colors", v)}
            placeholder="e.g. navy — press Enter"
          />

          <ChipInput
            label="Style tags"
            values={form.style_tags}
            onChange={(v) => setField("style_tags", v)}
            placeholder="e.g. casual — press Enter"
          />

          <div className="we-field-group">
            <label className="we-field-label" htmlFor="we-description">Description</label>
            <input
              id="we-description"
              className="we-field-input"
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
              placeholder="Short description"
            />
          </div>

          <div className="we-field-group">
            <label className="we-field-label" htmlFor="we-notes">Notes</label>
            <textarea
              id="we-notes"
              className="we-field-input we-textarea"
              value={form.user_notes}
              onChange={(e) => setField("user_notes", e.target.value)}
              placeholder="Personal notes (optional)"
              rows={2}
            />
          </div>

          {error && <p className="we-error">{error}</p>}

          <div className="we-actions">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
            <button type="button" className="btn-danger" onClick={handleDelete}>
              Delete Item
            </button>
          </div>

          {onBuildOutfit && (
            <button
              type="button"
              className="we-build-outfit-btn"
              onClick={() => onBuildOutfit(item)}
            >
              👔 Build Outfit Around This
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
