import React from "react";
import "./PasswordStrengthMeter.css";

function passwordScore(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Za-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (pw.length >= 12) score++;
  return score;
}

function strengthInfo(score) {
  if (score === 0) return { label: "", color: "", segments: 0 };
  if (score === 1) return { label: "Weak", color: "#ef4444", segments: 1 };
  if (score <= 3) return { label: "Medium", color: "#f59e0b", segments: 2 };
  return { label: "Strong", color: "#22c55e", segments: 3 };
}

export function passwordMeetsMinimum(pw) {
  return pw.length >= 8 && /[A-Za-z]/.test(pw) && /[0-9]/.test(pw);
}

export default function PasswordStrengthMeter({ password }) {
  const score = passwordScore(password);
  const { label, color, segments } = strengthInfo(score);

  const hasLength = password.length >= 8;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasLongLength = password.length >= 12;

  return (
    <>
      {password.length > 0 && (
        <div className="pw-strength">
          <div className="pw-strength-bar">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="pw-strength-seg"
                style={{ background: i < segments ? color : "#e5e7eb" }}
              />
            ))}
          </div>
          {label && (
            <span className="pw-strength-label" style={{ color }}>
              {label}
            </span>
          )}
        </div>
      )}
      <ul className="pw-checklist">
        <li className={`pw-check-item${hasLength ? " pw-check-item--met" : ""}`}>
          {hasLength ? "✓" : "○"} At least 8 characters
        </li>
        <li className={`pw-check-item${hasLetter ? " pw-check-item--met" : ""}`}>
          {hasLetter ? "✓" : "○"} Contains a letter
        </li>
        <li className={`pw-check-item${hasNumber ? " pw-check-item--met" : ""}`}>
          {hasNumber ? "✓" : "○"} Contains a number
        </li>
        <li className={`pw-check-item pw-check-item--bonus${hasLongLength ? " pw-check-item--met" : ""}`}>
          {hasLongLength ? "✓" : "○"} 12+ characters for a stronger password
        </li>
      </ul>
    </>
  );
}
