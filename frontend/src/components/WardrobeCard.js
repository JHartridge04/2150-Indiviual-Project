import React from "react";
import "./WardrobeCard.css";

export default function WardrobeCard({ item, onClick, onDelete }) {
  return (
    <div
      className="wardrobe-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <button
        type="button"
        className="wardrobe-card-delete"
        aria-label="Delete item"
        onClick={(e) => {
          e.stopPropagation();
          if (window.confirm("Delete this item from your wardrobe?")) {
            onDelete(item.id);
          }
        }}
      >
        ×
      </button>

      {item.image_url ? (
        <img
          src={item.image_url}
          alt={item.description || "Wardrobe item"}
          className="wardrobe-card-img"
        />
      ) : (
        <div className="wardrobe-card-img-placeholder">📷</div>
      )}

      <div className="wardrobe-card-info">
        <div className="wardrobe-card-badges">
          {item.category && (
            <span className="wardrobe-badge wardrobe-badge--category">
              {item.category}
            </span>
          )}
          <span className={`wardrobe-badge wardrobe-badge--${item.ownership}`}>
            {item.ownership}
          </span>
        </div>

        {item.colors?.length > 0 && (
          <div className="wardrobe-card-colors">
            {item.colors.slice(0, 3).map((c, i) => (
              <span key={i} className="wardrobe-color-chip">{c}</span>
            ))}
          </div>
        )}

        {item.description && (
          <p className="wardrobe-card-desc">{item.description}</p>
        )}
      </div>
    </div>
  );
}
