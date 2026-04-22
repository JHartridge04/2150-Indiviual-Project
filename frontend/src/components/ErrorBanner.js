import React from "react";
import "./ErrorBanner.css";
import { getErrorInfo } from "../utils/errorMessages";

export default function ErrorBanner({ message, onRetry, variant = "error", context }) {
  const { message: friendlyMsg, explanation } = getErrorInfo(message);
  const labelType = variant === "warning" ? "WARNING" : "ERROR";

  return (
    <div className={`ns-eb ns-eb--${variant}`}>
      <div className="ns-eb-body">
        <div className="ns-eb-sys">
          {context && (
            <>
              <span className="ns-eb-sys-context">{context}</span>
              <span className="ns-eb-sys-sep">›</span>
            </>
          )}
          <span className="ns-eb-sys-type">{labelType}</span>
        </div>
        <p className="ns-eb-message">{friendlyMsg}</p>
        <p className="ns-eb-explanation">{explanation}</p>
      </div>
      {onRetry && (
        <button className="ns-eb-retry" onClick={onRetry} type="button">
          RETRY
        </button>
      )}
    </div>
  );
}
