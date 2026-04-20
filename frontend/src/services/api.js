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
 * Change the authenticated user's password.
 * @param {string} currentPassword
 * @param {string} newPassword
 * @param {string} token - access token
 */
export async function changePassword(currentPassword, newPassword, token) {
  const res = await fetch(`${BASE_URL}/api/auth/change-password`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to change password");
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

// ---------------------------------------------------------------------------
// User profile
// ---------------------------------------------------------------------------

/**
 * Fetch the authenticated user's profile.
 * @param {string} token - access token
 */
export async function getProfile(token) {
  const res = await fetch(`${BASE_URL}/api/profile`, {
    method: "GET",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load profile");
  return data; // { profile: {...} | null }
}

/**
 * Create or update the authenticated user's profile.
 * @param {object} profileData - partial or full profile fields
 * @param {string} token       - access token
 */
export async function updateProfile(profileData, token) {
  const res = await fetch(`${BASE_URL}/api/profile`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(profileData),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to save profile");
  return data; // { profile: {...} }
}

// ---------------------------------------------------------------------------
// Style history
// ---------------------------------------------------------------------------

/**
 * Fetch the authenticated user's past style analyses, newest first.
 * @param {string} token - access token
 */
export async function getHistory(token) {
  const res = await fetch(`${BASE_URL}/api/history`, {
    method: "GET",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load history");
  return data; // { analyses: [...] }
}

/**
 * Delete a single style analysis by ID.
 * @param {string} id    - UUID of the style_analyses row
 * @param {string} token - access token
 */
export async function deleteHistoryItem(id, token) {
  const res = await fetch(`${BASE_URL}/api/history/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to delete analysis");
  return data; // { deleted: true }
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

/**
 * Fetch AI-powered recommendations for a style analysis (cache hit or fresh).
 * @param {string} analysisId - UUID of the style_analyses row
 * @param {string} token      - access token
 */
export async function getRecommendations(analysisId, token) {
  const res = await fetch(`${BASE_URL}/api/recommendations/${analysisId}`, {
    method: "POST",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load recommendations");
  return data; // { recommendations: [...], cached: bool }
}

/**
 * Clear the recommendation cache for an analysis then fetch fresh results.
 * @param {string} analysisId - UUID of the style_analyses row
 * @param {string} token      - access token
 */
export async function refreshRecommendations(analysisId, token) {
  const delRes = await fetch(`${BASE_URL}/api/recommendations/${analysisId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!delRes.ok) {
    const err = await delRes.json();
    throw new Error(err.error || "Failed to clear recommendation cache");
  }
  return getRecommendations(analysisId, token);
}

// ---------------------------------------------------------------------------
// Wardrobe
// ---------------------------------------------------------------------------

/**
 * Upload one or more clothing item photos and have them auto-tagged by AI.
 * @param {File[]} files     - image files to upload
 * @param {string} ownership - "owned" or "wishlist"
 * @param {string} token     - access token
 */
export async function uploadWardrobeItems(files, ownership, token) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  formData.append("ownership", ownership);

  const res = await fetch(`${BASE_URL}/api/wardrobe/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Upload failed");
  return data; // { items: [...], failures: [...] }
}

/**
 * Fetch the authenticated user's wardrobe items.
 * @param {string} token       - access token
 * @param {string} [ownership] - optional filter: "owned" or "wishlist"
 */
export async function getWardrobe(token, ownership) {
  const url = new URL(`${BASE_URL}/api/wardrobe`);
  if (ownership) url.searchParams.set("ownership", ownership);
  const res = await fetch(url.toString(), {
    method: "GET",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load wardrobe");
  return data; // { items: [...] }
}

/**
 * Update editable fields on a wardrobe item.
 * @param {string} itemId  - UUID of the wardrobe_items row
 * @param {object} updates - partial fields to update
 * @param {string} token   - access token
 */
export async function updateWardrobeItem(itemId, updates, token) {
  const res = await fetch(`${BASE_URL}/api/wardrobe/${itemId}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(updates),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to update item");
  return data; // { item: {...} }
}

/**
 * Delete a wardrobe item and its storage image.
 * @param {string} itemId - UUID of the wardrobe_items row
 * @param {string} token  - access token
 */
export async function deleteWardrobeItem(itemId, token) {
  const res = await fetch(`${BASE_URL}/api/wardrobe/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to delete item");
  return data; // { deleted: true }
}

/**
 * Derive style preferences from the user's wardrobe via Claude.
 * @param {string} token - access token
 */
export async function deriveStyleFromWardrobe(token) {
  const res = await fetch(`${BASE_URL}/api/wardrobe/derive-style`, {
    method: "POST",
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to derive style");
  return data; // { preferred_styles, color_palette, style_summary }
}

/**
 * Merge derived style suggestions into the user's profile.
 * @param {object} fields - profile fields to merge (arrays are unioned)
 * @param {string} token  - access token
 */
export async function applyDerivedStyle(fields, token) {
  const res = await fetch(`${BASE_URL}/api/profile/apply-derived`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(fields),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to apply style");
  return data; // { profile: {...} }
}

/**
 * Build a complete outfit around a single anchor wardrobe item.
 * @param {string} anchorItemId - UUID of the anchor wardrobe item
 * @param {string} occasion     - optional occasion context
 * @param {string} token        - access token
 */
export async function buildOutfit(anchorItemId, occasion, token) {
  const res = await fetch(`${BASE_URL}/api/wardrobe/build-outfit`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ anchor_item_id: anchorItemId, occasion }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to build outfit");
  return data; // { anchor_item_id, summary, wardrobe_pieces, missing_pieces }
}
