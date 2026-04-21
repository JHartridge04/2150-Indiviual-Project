import React, { useState } from "react";
import { Link } from "react-router-dom";
import { signUp } from "../services/api";
import PasswordStrengthMeter, { passwordMeetsMinimum } from "../components/PasswordStrengthMeter";
import AppHeader from "../components/AppHeader";
import "./Auth.css";
import "./Signup.css";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [pwError, setPwError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const meetsMinimum = passwordMeetsMinimum(password);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setPwError("");

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!meetsMinimum) {
      setPwError("Password does not meet the minimum requirements.");
      return;
    }

    setLoading(true);
    try {
      await signUp(email, password);
      setMessage(
        "Account created! Please check your email to confirm your address, then sign in."
      );
    } catch (err) {
      const msg = err.message || "Sign-up failed. Please try again.";
      if (/password/i.test(msg)) {
        setPwError(msg);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  if (message) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <AppHeader compact />
          <div className="auth-success">{message}</div>
          <Link to="/login" className="btn-primary" style={{ display: "block", textAlign: "center" }}>
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <AppHeader compact />
        <h2>Create Account</h2>

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
            placeholder="Min. 8 characters"
            required
            autoComplete="new-password"
          />

          <PasswordStrengthMeter password={password} />
          {pwError && <p className="pw-error">{pwError}</p>}

          <label htmlFor="confirm">Confirm Password</label>
          <input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repeat password"
            required
            autoComplete="new-password"
          />

          <button type="submit" disabled={loading || !meetsMinimum} className="btn-primary">
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
