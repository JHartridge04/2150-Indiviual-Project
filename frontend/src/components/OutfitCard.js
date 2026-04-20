/**
 * OutfitCard.js
 * A single card in the style-history grid.
 * Shows the outfit thumbnail and the analysis date.
 * When selected it receives the outfit-card--selected modifier.
 */

import React from "react";
import "./OutfitCard.css";

/**
 * @param {object}   props
 * @param {object}   props.analysis   - A style_analyses row from the backend
 * @param {boolean}  props.isSelected - Whether this card is currently expanded
 * @param {function} props.onClick    - Called when the card is clicked
 * @param {function} props.onDelete   - Called when the delete button is confirmed
 */
export default function OutfitCard({ analysis, isSelected, onClick, onDelete }) {
  const formattedDate = new Date(analysis.created_at).toLocaleDateString(
    "en-GB",
    { day: "numeric", month: "short", year: "numeric" }
  );

  function handleDelete(e) {
    e.stopPropagation();
    if (window.confirm("Delete this analysis? This cannot be undone.")) {
      onDelete(analysis.id);
    }
  }

  return (
    <button
      className={`outfit-card${isSelected ? " outfit-card--selected" : ""}`}
      onClick={onClick}
      aria-pressed={isSelected}
    >
      {analysis.image_url ? (
        <img
          src={analysis.image_url}
          alt="Outfit"
          className="outfit-card-image"
          loading="lazy"
        />
      ) : (
        <div className="outfit-card-placeholder">
          <span>No image</span>
        </div>
      )}
      <div className="outfit-card-body">
        <span className="outfit-card-date">{formattedDate}</span>
      </div>
      <button
        className="outfit-card-delete"
        onClick={handleDelete}
        aria-label="Delete analysis"
        title="Delete"
      >
        &times;
      </button>
    </button>
  );
}
