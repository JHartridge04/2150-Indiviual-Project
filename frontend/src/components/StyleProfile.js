/**
 * StyleProfile.js
 * Displays the AI analysis result: colours, silhouettes, style tags,
 * and a written summary.
 */

import React from "react";
import "./StyleProfile.css";

/**
 * @param {object} props
 * @param {{ colors: string[], silhouettes: string[], style_tags: string[], summary: string }} props.profile
 * @param {string|null} props.imageUrl
 */
export default function StyleProfile({ profile, imageUrl }) {
  const { colors = [], silhouettes = [], style_tags = [], summary = "" } = profile;

  return (
    <div className="profile-card">
      {/* Side-by-side: image + attributes */}
      <div className="profile-top">
        {imageUrl && (
          <img src={imageUrl} alt="Analysed outfit" className="profile-image" />
        )}

        <div className="profile-attributes">
          {/* Colour swatches */}
          {colors.length > 0 && (
            <div className="attr-group">
              <h3>Colours</h3>
              <div className="color-list">
                {colors.map((c) => (
                  <span key={c} className="color-chip">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Silhouettes */}
          {silhouettes.length > 0 && (
            <div className="attr-group">
              <h3>Silhouettes</h3>
              <div className="tag-row">
                {silhouettes.map((s) => (
                  <span key={s} className="badge badge-blue">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Style tags */}
          {style_tags.length > 0 && (
            <div className="attr-group">
              <h3>Style Tags</h3>
              <div className="tag-row">
                {style_tags.map((t) => (
                  <span key={t} className="badge badge-purple">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Style summary */}
      {summary && (
        <div className="profile-summary">
          <h3>Style Summary</h3>
          <p>{summary}</p>
        </div>
      )}
    </div>
  );
}
