/**
 * Profile.js
 * Lets the authenticated user view and edit their style profile.
 * Profile data feeds into AI analysis and recommendation prompts.
 */

import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getProfile, updateProfile, changePassword } from "../services/api";
import PasswordStrengthMeter, { passwordMeetsMinimum } from "../components/PasswordStrengthMeter";
import "./Profile.css";

// ---------------------------------------------------------------------------
// Chip input — "type and press Enter to add"
// ---------------------------------------------------------------------------
function ChipInput({ label, values, onChange, placeholder }) {
  const [input, setInput] = useState("");

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = input.trim();
      if (trimmed && !values.includes(trimmed)) {
        onChange([...values, trimmed]);
      }
      setInput("");
    }
  }

  return (
    <div className="field-group">
      <label className="field-label">{label}</label>
      <div className="chip-wrap">
        {values.map((v) => (
          <span key={v} className="chip">
            {v}
            <button
              type="button"
              className="chip-remove"
              aria-label={`Remove ${v}`}
              onClick={() => onChange(values.filter((x) => x !== v))}
            >
              ×
            </button>
          </span>
        ))}
        <input
          className="chip-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Type and press Enter"}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
const EMPTY_PROFILE = {
  gender: "",
  age_range: "",
  body_type: "",
  height_cm: "",
  weight_kg: "",
  preferred_styles: [],
  favorite_brands: [],
  occasions: [],
  shirt_size: "",
  pants_size: "",
  shoe_size: "",
  budget_min_usd: "",
  budget_max_usd: "",
};

export default function Profile() {
  const { user, token } = useAuth();
  const [form, setForm] = useState(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" }); // type: "success"|"error"

  // Change-password state
  const [pwForm, setPwForm] = useState({ current: "", newPw: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMessage, setPwMessage] = useState({ text: "", type: "" });

  // -------------------------------------------------------------------------
  // Load existing profile
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!token) return;
    async function load() {
      try {
        const data = await getProfile(token);
        if (data.profile) {
          setForm({
            ...EMPTY_PROFILE,
            ...Object.fromEntries(
              Object.entries(data.profile).map(([k, v]) => [k, v ?? EMPTY_PROFILE[k] ?? ""])
            ),
          });
        }
      } catch (err) {
        setMessage({ text: err.message || "Failed to load profile.", type: "error" });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  // -------------------------------------------------------------------------
  // Field change helpers
  // -------------------------------------------------------------------------
  const setField = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setField(name, value);
  }

  // -------------------------------------------------------------------------
  // Save
  // -------------------------------------------------------------------------
  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setMessage({ text: "", type: "" });

    // Build payload: convert empty strings to null, keep arrays as-is
    const payload = {};
    for (const [key, val] of Object.entries(form)) {
      if (Array.isArray(val)) {
        payload[key] = val;
      } else if (val === "" || val === null || val === undefined) {
        payload[key] = null;
      } else if (["height_cm", "weight_kg", "budget_min_usd", "budget_max_usd"].includes(key)) {
        const parsed = parseInt(val, 10);
        payload[key] = isNaN(parsed) ? null : parsed;
      } else {
        payload[key] = val;
      }
    }

    try {
      await updateProfile(payload, token);
      setMessage({ text: "Profile saved!", type: "success" });
    } catch (err) {
      setMessage({ text: err.message || "Failed to save profile.", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  // -------------------------------------------------------------------------
  // Change password
  // -------------------------------------------------------------------------
  async function handleChangePassword(e) {
    e.preventDefault();
    setPwMessage({ text: "", type: "" });

    if (pwForm.newPw !== pwForm.confirm) {
      setPwMessage({ text: "New passwords do not match.", type: "error" });
      return;
    }

    setPwSaving(true);
    try {
      await changePassword(pwForm.current, pwForm.newPw, token);
      setPwMessage({ text: "Password changed successfully.", type: "success" });
      setPwForm({ current: "", newPw: "", confirm: "" });
    } catch (err) {
      setPwMessage({ text: err.message || "Failed to change password.", type: "error" });
    } finally {
      setPwSaving(false);
    }
  }

  const pwCanSubmit =
    pwForm.current.length > 0 &&
    passwordMeetsMinimum(pwForm.newPw) &&
    pwForm.newPw === pwForm.confirm;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="profile-container">
      <header className="home-header">
        <h1 className="app-title">👗 Style Assistant</h1>
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/" className="btn-secondary">Upload</Link>
          <Link to="/history" className="btn-secondary">History</Link>
          <Link to="/wardrobe" className="btn-secondary">Wardrobe</Link>
          <Link to="/logout" className="btn-outline">Sign Out</Link>
        </nav>
      </header>

      <main className="profile-main">
        <h2 className="profile-heading">My Style Profile</h2>
        <p className="profile-subtitle">
          This information personalises your AI analysis and product recommendations.
        </p>

        {loading ? (
          <div className="loading-spinner">Loading profile…</div>
        ) : (
          <form onSubmit={handleSubmit} className="profile-form">

            {/* ----- Basic ----- */}
            <section className="profile-card">
              <h3 className="card-title">Basic</h3>

              <div className="field-group">
                <label className="field-label" htmlFor="gender">Gender</label>
                <select id="gender" name="gender" className="field-input" value={form.gender} onChange={handleChange}>
                  <option value="">Prefer not to say</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="non-binary">Non-binary</option>
                </select>
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="age_range">Age range</label>
                <select id="age_range" name="age_range" className="field-input" value={form.age_range} onChange={handleChange}>
                  <option value="">Select…</option>
                  <option value="under 18">Under 18</option>
                  <option value="18-24">18–24</option>
                  <option value="25-34">25–34</option>
                  <option value="35-44">35–44</option>
                  <option value="45-54">45–54</option>
                  <option value="55+">55+</option>
                </select>
              </div>
            </section>

            {/* ----- Body ----- */}
            <section className="profile-card">
              <h3 className="card-title">Body &amp; Sizes</h3>

              <div className="field-group">
                <label className="field-label" htmlFor="body_type">Body type</label>
                <input id="body_type" name="body_type" className="field-input" value={form.body_type} onChange={handleChange} placeholder="e.g. athletic, slim, curvy" />
              </div>

              <div className="field-row">
                <div className="field-group">
                  <label className="field-label" htmlFor="height_cm">Height (cm)</label>
                  <input id="height_cm" name="height_cm" type="number" min="0" className="field-input" value={form.height_cm} onChange={handleChange} placeholder="170" />
                </div>
                <div className="field-group">
                  <label className="field-label" htmlFor="weight_kg">Weight (kg)</label>
                  <input id="weight_kg" name="weight_kg" type="number" min="0" className="field-input" value={form.weight_kg} onChange={handleChange} placeholder="70" />
                </div>
              </div>

              <div className="field-row">
                <div className="field-group">
                  <label className="field-label" htmlFor="shirt_size">Shirt size</label>
                  <input id="shirt_size" name="shirt_size" className="field-input" value={form.shirt_size} onChange={handleChange} placeholder="M" />
                </div>
                <div className="field-group">
                  <label className="field-label" htmlFor="pants_size">Pants size</label>
                  <input id="pants_size" name="pants_size" className="field-input" value={form.pants_size} onChange={handleChange} placeholder='32"' />
                </div>
                <div className="field-group">
                  <label className="field-label" htmlFor="shoe_size">Shoe size</label>
                  <input id="shoe_size" name="shoe_size" className="field-input" value={form.shoe_size} onChange={handleChange} placeholder="10" />
                </div>
              </div>
            </section>

            {/* ----- Style ----- */}
            <section className="profile-card">
              <h3 className="card-title">Style Preferences</h3>

              <ChipInput
                label="Preferred styles"
                values={form.preferred_styles}
                onChange={(v) => setField("preferred_styles", v)}
                placeholder="e.g. streetwear — press Enter"
              />
              <ChipInput
                label="Favourite brands"
                values={form.favorite_brands}
                onChange={(v) => setField("favorite_brands", v)}
                placeholder="e.g. Nike — press Enter"
              />
              <ChipInput
                label="Occasions"
                values={form.occasions}
                onChange={(v) => setField("occasions", v)}
                placeholder="e.g. work, casual — press Enter"
              />
            </section>

            {/* ----- Budget ----- */}
            <section className="profile-card">
              <h3 className="card-title">Budget (USD)</h3>
              <div className="field-row">
                <div className="field-group">
                  <label className="field-label" htmlFor="budget_min_usd">Min ($)</label>
                  <input id="budget_min_usd" name="budget_min_usd" type="number" min="0" className="field-input" value={form.budget_min_usd} onChange={handleChange} placeholder="0" />
                </div>
                <div className="field-group">
                  <label className="field-label" htmlFor="budget_max_usd">Max ($)</label>
                  <input id="budget_max_usd" name="budget_max_usd" type="number" min="0" className="field-input" value={form.budget_max_usd} onChange={handleChange} placeholder="200" />
                </div>
              </div>
            </section>

            {message.text && (
              <p className={`profile-message profile-message--${message.type}`}>
                {message.text}
              </p>
            )}

            <button type="submit" className="btn-primary profile-save" disabled={saving}>
              {saving ? "Saving…" : "Save Profile"}
            </button>

          </form>
        )}

        {/* ----------------------------------------------------------------- */}
        {/* Change Password                                                    */}
        {/* ----------------------------------------------------------------- */}
        {!loading && (
          <form onSubmit={handleChangePassword} className="profile-form" style={{ marginTop: "1.5rem" }}>
            <section className="profile-card">
              <h3 className="card-title">Change Password</h3>

              <div className="field-group">
                <label className="field-label" htmlFor="pw-current">Current password</label>
                <input
                  id="pw-current"
                  type="password"
                  className="field-input"
                  value={pwForm.current}
                  onChange={(e) => setPwForm((p) => ({ ...p, current: e.target.value }))}
                  placeholder="Your current password"
                  autoComplete="current-password"
                />
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="pw-new">New password</label>
                <input
                  id="pw-new"
                  type="password"
                  className="field-input"
                  value={pwForm.newPw}
                  onChange={(e) => setPwForm((p) => ({ ...p, newPw: e.target.value }))}
                  placeholder="Min. 8 characters"
                  autoComplete="new-password"
                />
                <PasswordStrengthMeter password={pwForm.newPw} />
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="pw-confirm">Confirm new password</label>
                <input
                  id="pw-confirm"
                  type="password"
                  className="field-input"
                  value={pwForm.confirm}
                  onChange={(e) => setPwForm((p) => ({ ...p, confirm: e.target.value }))}
                  placeholder="Repeat new password"
                  autoComplete="new-password"
                />
              </div>

              {pwMessage.text && (
                <p className={`profile-message profile-message--${pwMessage.type}`}>
                  {pwMessage.text}
                </p>
              )}

              <button type="submit" className="btn-primary profile-save" disabled={pwSaving || !pwCanSubmit}>
                {pwSaving ? "Updating…" : "Change Password"}
              </button>
            </section>
          </form>
        )}
      </main>
    </div>
  );
}
