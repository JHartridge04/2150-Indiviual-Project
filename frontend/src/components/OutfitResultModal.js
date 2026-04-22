import React from "react";
import "./OutfitResultModal.css";
import RecommendationCard from "./RecommendationCard";
import Skeleton from "./Skeleton";
import ProgressBar from "./ProgressBar";

const OUTFIT_MSGS = [
  "READING ANCHOR ITEM...",
  "SEARCHING WARDROBE FOR MATCHES...",
  "CHECKING COLOUR HARMONY...",
  "ASSEMBLING OUTFIT LAYERS...",
  "FINALISING SUGGESTION...",
];

function OutfitBuilderSkeleton({ anchorItem }) {
  return (
    <div className="orm-skel-wrap">
      <div className="orm-section">
        <h4 className="orm-section-title">Anchor Item</h4>
        <div className="orm-anchor-card">
          {anchorItem?.image_url ? (
            <img src={anchorItem.image_url} alt="Anchor" className="orm-anchor-img" />
          ) : (
            <Skeleton width={80} height={100} style={{ flexShrink: 0 }} />
          )}
          <div className="orm-skel-anchor-lines">
            <Skeleton width="58%" height={8} />
            <Skeleton width="84%" height={7} />
            <div className="orm-skel-tags-row">
              <Skeleton width={42} height={17} />
              <Skeleton width={55} height={17} />
              <Skeleton width={40} height={17} />
            </div>
          </div>
        </div>
      </div>

      <div className="orm-skel-progress">
        <ProgressBar messages={OUTFIT_MSGS} intervalMs={2400} prefix="SYS/BUILD >" />
      </div>

      <div className="orm-section">
        <h4 className="orm-section-title">Suggested Pieces</h4>
        <div className="orm-skel-pieces-grid">
          {[0, 1, 2].map((i) => (
            <div key={i} className="orm-skel-piece-card">
              <Skeleton height={82} />
              <div className="orm-skel-piece-info">
                <Skeleton width="48%" height={8} style={{ background: "var(--ns-accent)", opacity: 0.22 }} />
                <Skeleton width="88%" height={6} />
                <Skeleton width="62%" height={6} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="orm-section">
        <h4 className="orm-section-title">Complete Look</h4>
        <div className="orm-skel-look-strip">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className={`orm-skel-look-thumb${i === 0 ? " orm-skel-look-thumb--anchor" : ""}`}>
              <Skeleton height={50} />
              {i === 0 && <div className="orm-skel-accent-dot" />}
            </div>
          ))}
        </div>
        <Skeleton height={28} />
      </div>
    </div>
  );
}

export default function OutfitResultModal({ anchorItem, wardrobeItems, result, loading, onClose }) {
  const wardrobeById = Object.fromEntries((wardrobeItems || []).map((i) => [i.id, i]));

  return (
    <div className="orm-overlay" onClick={onClose}>
      <div className="orm-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="orm-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        {loading ? (
          <OutfitBuilderSkeleton anchorItem={anchorItem} />
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}
