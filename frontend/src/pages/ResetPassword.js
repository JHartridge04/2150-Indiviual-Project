import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import supabase from "../services/supabaseClient";
import PasswordStrengthMeter, { passwordMeetsMinimum } from "../components/PasswordStrengthMeter";
import AppHeader from "../components/AppHeader";
import "./Auth.css";
import "./ResetPassword.css";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [sessionReady, setSessionReady] = useState(null); // null = checking, true/false = resolved
  const [newPw, setNewPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSessionReady(!!(data.session));
    });
  }, []);

  const meetsMinimum = passwordMeetsMinimum(newPw);
  const canSubmit = meetsMinimum && newPw === confirm;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!canSubmit) return;

    setSaving(true);
    try {
      const { error: updateError } = await supabase.auth.updateUser({ password: newPw });
      if (updateError) throw updateError;
      setDone(true);
      await supabase.auth.signOut();
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(err.message || "Failed to set new password. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  // Still checking session
  if (sessionReady === null) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <AppHeader compact />
          <p className="rp-checking">Checking reset link…</p>
        </div>
      </div>
    );
  }

  // Invalid / expired link
  if (!sessionReady) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <AppHeader compact />
          <div className="auth-error">This reset link is invalid or has expired.</div>
          <Link to="/login" className="btn-primary" style={{ display: "block", textAlign: "center", marginTop: "1rem" }}>
            Back to Sign In
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  if (done) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <AppHeader compact />
          <div className="auth-success">
            Password updated! Redirecting you to sign in…
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <AppHeader compact />
        <h2>Set New Password</h2>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="rp-new">New password</label>
          <input
            id="rp-new"
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            placeholder="Min. 8 characters"
            required
            autoComplete="new-password"
          />
          <PasswordStrengthMeter password={newPw} />

          <label htmlFor="rp-confirm">Confirm new password</label>
          <input
            id="rp-confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repeat new password"
            required
            autoComplete="new-password"
          />

          <button type="submit" disabled={saving || !canSubmit} className="btn-primary">
            {saving ? "Saving…" : "Set New Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
