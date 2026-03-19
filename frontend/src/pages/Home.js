/**
 * Home.js
 * The main dashboard.  Authenticated users can:
 *   1. Upload an outfit photo
 *   2. Trigger AI style analysis
 *   3. View the resulting style profile
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { uploadPhoto, analyzeStyle } from "../services/api";
import StyleProfile from "../components/StyleProfile";
import "./Home.css";

export default function Home() {
  const { user, token } = useAuth();

  // Upload / analysis state
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analysing, setAnalysing] = useState(false);
  const [uploadedUrl, setUploadedUrl] = useState(null);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  // -------------------------------------------------------------------------
  // File selection
  // -------------------------------------------------------------------------
  function handleFileChange(e) {
    const selected = e.target.files[0];
    if (!selected) return;

    // Client-side type guard
    if (!selected.type.startsWith("image/")) {
      setError("Please select an image file (JPEG, PNG, WebP, or GIF).");
      return;
    }

    setFile(selected);
    setError("");
    setProfile(null);
    setUploadedUrl(null);

    // Generate a local preview URL
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result);
    reader.readAsDataURL(selected);
  }

  // -------------------------------------------------------------------------
  // Upload → Analyse pipeline
  // -------------------------------------------------------------------------
  async function handleUpload(e) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a photo first.");
      return;
    }

    setError("");

    try {
      // Step 1 — upload to Supabase via Flask
      setUploading(true);
      const { url } = await uploadPhoto(file, token);
      setUploadedUrl(url);
      setUploading(false);

      // Step 2 — send to Claude for style analysis
      setAnalysing(true);
      const result = await analyzeStyle(url, token);
      setProfile(result);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setUploading(false);
      setAnalysing(false);
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="home-container">
      {/* Header */}
      <header className="home-header">
        <h1 className="app-title">👗 Style Assistant</h1>
        <nav className="home-nav">
          <span className="nav-email">{user?.email}</span>
          <Link to="/recommendations" className="btn-secondary">
            Recommendations
          </Link>
          <Link to="/logout" className="btn-outline">
            Sign Out
          </Link>
        </nav>
      </header>

      <main className="home-main">
        <section className="upload-section">
          <h2>Upload Your Outfit</h2>
          <p className="section-subtitle">
            Upload a photo of your outfit and get an AI-powered style analysis.
          </p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleUpload} className="upload-form">
            {/* Drop / file input zone */}
            <label htmlFor="photo-input" className="upload-zone">
              {preview ? (
                <img src={preview} alt="Outfit preview" className="upload-preview" />
              ) : (
                <div className="upload-placeholder">
                  <span className="upload-icon">📷</span>
                  <span>Click to choose a photo</span>
                  <span className="upload-hint">JPEG · PNG · WebP · GIF</span>
                </div>
              )}
            </label>
            <input
              id="photo-input"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />

            <button
              type="submit"
              className="btn-primary"
              disabled={!file || uploading || analysing}
            >
              {uploading
                ? "Uploading…"
                : analysing
                ? "Analysing with AI…"
                : "Upload & Analyse"}
            </button>
          </form>
        </section>

        {/* Style profile results */}
        {profile && (
          <section className="profile-section">
            <h2>Your Style Profile</h2>
            <StyleProfile profile={profile} imageUrl={uploadedUrl} />

            <div className="cta-row">
              <Link
                to="/recommendations"
                state={{ styleTags: profile.style_tags }}
                className="btn-primary"
              >
                Get Recommendations →
              </Link>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
