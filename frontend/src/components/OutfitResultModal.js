import React from "react";
import "./OutfitResultModal.css";
import RecommendationCard from "./RecommendationCard";

export default function OutfitResultModal({ anchorItem, wardrobeItems, result, onClose }) {
  const wardrobeById = Object.fromEntries((wardrobeItems || []).map((i) => [i.id, i]));

  return (
    <div className="orm-overlay" onClick={onClose}>
      <div className="orm-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="orm-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <h3 className="orm-title">Your Outfit</h3>
        {result.summary && <p className="orm-summary">{result.summary}</p>}

        {/* Anchor item */}
        <div className="orm-section">
          <h4 className="orm-section-title">Anchor Item</h4>
          <div className="orm-anchor-card">
            {anchorItem.image_url ? (
              <img
                src={anchorItem.image_url}
                alt={anchorItem.description || "Anchor item"}
                className="orm-anchor-img"
              />
            ) : (
              <div className="orm-img-placeholder">📷</div>
            )}
            <div className="orm-anchor-info">
              {anchorItem.category && (
                <span className="wardrobe-badge wardrobe-badge--category">
                  {anchorItem.category}
                </span>
              )}
              {anchorItem.description && (
                <p className="orm-item-desc">{anchorItem.description}</p>
              )}
              {anchorItem.colors?.length > 0 && (
                <div className="orm-color-chips">
                  {anchorItem.colors.slice(0, 4).map((c, i) => (
                    <span key={i} className="wardrobe-color-chip">{c}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Pieces from wardrobe */}
        {result.wardrobe_pieces?.length > 0 && (
          <div className="orm-section">
            <h4 className="orm-section-title">From Your Wardrobe</h4>
            <div className="orm-pieces-grid">
              {result.wardrobe_pieces.map((piece, i) => {
                const item = wardrobeById[piece.item_id];
                if (!item) return null;
                return (
                  <div key={i} className="orm-piece-card">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.description || piece.role}
                        className="orm-piece-img"
                      />
                    ) : (
                      <div className="orm-img-placeholder orm-img-placeholder--small">📷</div>
                    )}
                    <div className="orm-piece-info">
                      <span className="wardrobe-badge wardrobe-badge--category">{piece.role}</span>
                      <p className="orm-piece-reason">{piece.reason}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Missing pieces */}
        {result.missing_pieces?.length > 0 && (
          <div className="orm-section">
            <h4 className="orm-section-title">What's Missing</h4>
            <ul className="orm-missing-list">
              {result.missing_pieces.map((piece, i) => (
                <li key={i} className="orm-missing-item">
                  <div className="orm-missing-header">
                    <span className="wardrobe-badge wardrobe-badge--category orm-missing-role">
                      {piece.role}
                    </span>
                    <span className="orm-missing-desc">{piece.description}</span>
                  </div>
                  {piece.products?.length > 0 && (
                    <div className="orm-missing-products">
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
      </div>
    </div>
  );
}
