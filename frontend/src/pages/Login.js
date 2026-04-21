import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import supabase from "../services/supabaseClient";
import AppHeader from "../components/AppHeader";
import "./Auth.css";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Forgot-password inline state
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotMsg, setForgotMsg] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleForgot(e) {
    e.preventDefault();
    setForgotLoading(true);
    setForgotMsg("");
    try {
      await supabase.auth.resetPasswordForEmail(forgotEmail, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
    } catch (_) {
      // Swallow errors — never reveal whether an account exists
    } finally {
      setForgotLoading(false);
      setForgotMsg("If an account exists for that email, a reset link has been sent.");
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <AppHeader compact />
        <h2>Sign In</h2>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoComplete="email"
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            autoComplete="current-password"
          />

          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Signing in…" : "Sign In"}
          </button>

          <button
            type="button"
            className="auth-forgot-btn"
            onClick={() => { setShowForgot((v) => !v); setForgotMsg(""); }}
          >
            Forgot password?
          </button>
        </form>

        {showForgot && (
          <div className="auth-forgot-panel">
            {forgotMsg ? (
              <p className="auth-forgot-msg">{forgotMsg}</p>
            ) : (
              <form onSubmit={handleForgot} className="auth-form">
                <label htmlFor="forgot-email">Your email address</label>
                <input
                  id="forgot-email"
                  type="email"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                />
                <button type="submit" disabled={forgotLoading} className="btn-secondary">
                  {forgotLoading ? "Sending…" : "Send reset link"}
                </button>
              </form>
            )}
          </div>
        )}

        <p className="auth-switch">
          Don't have an account?{" "}
          <Link to="/signup">Create one</Link>
        </p>
      </div>
    </div>
  );
}
