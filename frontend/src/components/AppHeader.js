import React from 'react';
import './AppHeader.css';

export default function AppHeader({ compact = false }) {
  return (
    <div className={compact ? 'app-header app-header--compact' : 'app-header'}>
      <div className="app-header-wordmark">NO STYLIST</div>
      <p className="app-header-blurb">
        AI-powered style analysis, wardrobe management, and streetwear recommendations.
      </p>
      {!compact && (
        <>
          <hr className="app-header-rule" />
          <span className="app-header-meta">
            SYS/01 <span className="app-header-dot">•</span> v1.0
          </span>
        </>
      )}
    </div>
  );
}
