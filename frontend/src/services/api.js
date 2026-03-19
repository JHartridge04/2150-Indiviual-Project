/**
 * api.js
 * Thin wrapper around the Flask backend API.
 * All requests include the Supabase access token in the Authorization header.
 */

const BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5000";

/**
 * Build standard headers for authenticated requests.
 * @param {string|null} token - Supabase JWT access token
 */
function authHeaders(token) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/**
 * Sign up a new user via the Flask backend.
 * @param {string} email
 * @param {string} password
 */
export async function signUp(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Sign-up failed");
  return data;
}

/**
 * Log in an existing user via the Flask backend.
 * @param {string} email
 * @param {string} password
 */
export async function logIn(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Login failed");
  return data;
}

/**
 * Log out the current session.
 * @param {string} token - access token
 */
export async function logOut(token) {
  const res = await fetch(`${BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Logout failed");
  return data;
}

// ---------------------------------------------------------------------------
// Photo upload
// ---------------------------------------------------------------------------

/**
 * Upload an outfit photo to Supabase Storage via the Flask backend.
 * @param {File} file - The image file to upload
 * @param {string} token - access token
 */
export async function uploadPhoto(file, token) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Upload failed");
  return data; // { path, url }
}

// ---------------------------------------------------------------------------
// Style analysis
// ---------------------------------------------------------------------------

/**
 * Send an image URL to Claude for style analysis.
 * @param {string} imageUrl - Public URL of the uploaded image
 * @param {string} token - access token
 */
export async function analyzeStyle(imageUrl, token) {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ image_url: imageUrl }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Analysis failed");
  return data; // { colors, silhouettes, style_tags, summary }
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

/**
 * Fetch clothing recommendations based on style tags.
 * @param {string[]} styleTags - Array of style tag strings
 * @param {string} token - access token
 */
export async function getRecommendations(styleTags, token) {
  const res = await fetch(`${BASE_URL}/api/recommendations`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ style_tags: styleTags }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load recommendations");
  return data; // { recommendations: [...] }
}
