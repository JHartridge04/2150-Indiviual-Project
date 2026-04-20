"""
AI-Powered Personal Style Assistant — Flask Backend
Provides RESTful API endpoints for user auth, photo upload,
AI style analysis via Claude, and style-based recommendations.
"""

import io
import logging
import os
import re
import uuid
import base64
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from PIL import Image

import requests as req_lib

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client, ClientOptions

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

load_dotenv()  # Load environment variables from .env

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validate required environment variables at startup
# ---------------------------------------------------------------------------

_REQUIRED_ENV_VARS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "ANTHROPIC_API_KEY", "RAPIDAPI_KEY")
_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Please check your .env file."
    )

app = Flask(__name__)

# CORS_ORIGINS accepts a comma-separated list of allowed origins, e.g.:
#   CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app
# Defaults to "*" for local dev when the variable is unset.
_raw_origins = os.getenv("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]
CORS(app, resources={r"/api/*": {"origins": _cors_origins}})

# ---------------------------------------------------------------------------
# Supabase client (shared across requests)
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ---------------------------------------------------------------------------
# RapidAPI (Real-Time Product Search)
# ---------------------------------------------------------------------------

RAPIDAPI_KEY: str = os.environ["RAPIDAPI_KEY"]
RAPIDAPI_HOST = "real-time-product-search.p.rapidapi.com"

# Storage bucket for outfit photos
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "outfit-photos")

# Storage bucket for wardrobe item photos
WARDROBE_BUCKET = os.getenv("WARDROBE_BUCKET", "wardrobe-items")

# Maximum allowed upload size (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Claude's limit is 5 MB on the base64-encoded string, not the raw bytes.
# Base64 inflates size by 4/3, so the raw image must stay under 5 MB × 3/4 = 3.75 MB.
# We use 3.5 MB for a comfortable safety margin.
MAX_CLAUDE_IMAGE_BYTES = int(3.5 * 1024 * 1024)


def _compress_image_bytes(image_bytes: bytes, media_type: str) -> tuple[bytes, str]:
    """
    Return (bytes, media_type) compressed to under MAX_CLAUDE_IMAGE_BYTES.

    If the image is already small enough it is returned unchanged.
    Otherwise Pillow re-encodes it as JPEG, first by stepping down quality
    (85 → 70 → 55 → 40 → 25), then by halving dimensions until it fits.
    media_type is updated to image/jpeg whenever re-encoding happens.
    """
    if len(image_bytes) <= MAX_CLAUDE_IMAGE_BYTES:
        return image_bytes, media_type

    img = Image.open(io.BytesIO(image_bytes))

    # JPEG does not support transparency — flatten to RGB/L
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    def _encode(image: Image.Image, quality: int) -> bytes:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    # Phase 1: lower quality only (no dimension change)
    for quality in (85, 70, 55, 40, 25):
        compressed = _encode(img, quality)
        if len(compressed) <= MAX_CLAUDE_IMAGE_BYTES:
            logger.info(
                "Image compressed to %.2f MB at quality=%d",
                len(compressed) / 1_048_576,
                quality,
            )
            return compressed, "image/jpeg"

    # Phase 2: halve dimensions repeatedly at quality=55
    while img.width > 200 and img.height > 200:
        img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
        compressed = _encode(img, 55)
        if len(compressed) <= MAX_CLAUDE_IMAGE_BYTES:
            logger.info(
                "Image compressed to %.2f MB at %dx%d",
                len(compressed) / 1_048_576,
                img.width,
                img.height,
            )
            return compressed, "image/jpeg"

    # Best-effort: return whatever size we reached
    logger.warning(
        "Could not compress image below 4.5 MB; sending %.2f MB",
        len(compressed) / 1_048_576,
    )
    return compressed, "image/jpeg"

# Email format validation regex — basic sanity check (local-part @ domain.tld)
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
)



# ---------------------------------------------------------------------------
# Security response headers
# ---------------------------------------------------------------------------

@app.after_request
def set_security_headers(response):
    """Attach security-related HTTP headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _auth_header() -> str | None:
    """Extract the Bearer token from the incoming request's Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


def _require_token():
    """Return (token, error_response) tuple. error_response is None when valid."""
    token = _auth_header()
    if not token:
        return None, (jsonify({"error": "Missing or invalid Authorization header"}), 401)
    return token, None


def _safe_image_url(url: str):
    """
    Validate *url* and return a *reconstructed* safe URL string (or None on
    failure together with an error message).

    Only HTTPS URLs whose hostname matches the configured Supabase project
    domain are accepted, preventing Server-Side Request Forgery (SSRF).

    The URL is *reconstructed* from its parsed components (not returned as-is)
    so that the value passed to requests.get() is never the raw user string.

    Returns: (safe_url: str, error: None)  or  (None, error_message: str)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return None, "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return None, "Only http and https URLs are allowed"

    hostname = parsed.hostname
    if not hostname:
        return None, "URL must have a hostname"

    try:
        allowed_hostname = urlparse(SUPABASE_URL).hostname or ""
    except Exception:
        allowed_hostname = ""

    if not allowed_hostname or hostname != allowed_hostname:
        return None, (
            "image_url must point to the configured Supabase project "
            f"(expected host: {allowed_hostname})"
        )

    # Reconstruct URL from validated components — never use the raw user string
    safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        safe_url += f"?{parsed.query}"

    return safe_url, None


# ---------------------------------------------------------------------------
# Style history helper
# ---------------------------------------------------------------------------

def save_analysis(user_id: str, image_url: str | None, analysis: dict, access_token: str) -> str | None:
    """
    Persist a completed style analysis to the style_analyses table and return
    the new row's UUID, or None if the insert failed.

    A per-request Supabase client is created with the user's JWT so that the
    insert runs as the authenticated user and satisfies the RLS policy
    ``auth.uid() = user_id``.

    Non-fatal: any exception is logged but never re-raised so that a database
    failure cannot break the /api/analyze response.
    """
    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
        )
        resp = user_supabase.table("style_analyses").insert({
            "user_id": user_id,
            "image_url": image_url or "",
            "colors": analysis.get("colors", []),
            "silhouettes": analysis.get("silhouettes", []),
            "style_tags": analysis.get("style_tags", []),
            "summary": analysis.get("summary", ""),
        }).execute()
        inserted_id: str | None = resp.data[0]["id"] if resp.data else None
        logger.info("Saved style analysis for user %s (id=%s)", user_id, inserted_id)
        return inserted_id
    except Exception as exc:
        logger.error("Failed to save style analysis for user %s: %s", user_id, exc)
        return None


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

def validate_password(password: str) -> tuple[bool, str]:
    """Return (True, "") if password meets requirements, else (False, error_message)."""
    if not password:
        return False, "Password is required"
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, ""


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    """
    Register a new user with Supabase Auth.

    Request JSON: { "email": str, "password": str }
    Response JSON: { "user": {...}, "session": {...} }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400

    valid, pw_error = validate_password(password)
    if not valid:
        return jsonify({"error": pw_error}), 400

    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        logger.info("Signup succeeded for %s", email)
        return jsonify({
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None,
        }), 201
    except Exception as exc:
        logger.warning("Signup failed for %s: %s", email, exc)
        return jsonify({"error": str(exc)}), 400


@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticate an existing user.

    Request JSON: { "email": str, "password": str }
    Response JSON: { "user": {...}, "session": {...} }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        logger.info("Login succeeded for %s", email)
        return jsonify({
            "user": response.user.model_dump() if response.user else None,
            "session": response.session.model_dump() if response.session else None,
        }), 200
    except Exception as exc:
        logger.warning("Login failed for %s: %s", email, exc)
        return jsonify({"error": str(exc)}), 401


@app.route("/api/auth/change-password", methods=["POST"])
def change_password():
    """
    Change the authenticated user's password.

    Requires: Authorization: Bearer <access_token>
    Request JSON: { "current_password": str, "new_password": str }
    Response JSON: { "success": true }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_obj = user_supabase.auth.get_user(token).user
        user_id = user_obj.id
        user_email = user_obj.email
    except Exception as exc:
        logger.warning("change_password: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")

    if not current_password:
        return jsonify({"error": "current_password is required"}), 400

    valid, pw_error = validate_password(new_password)
    if not valid:
        return jsonify({"error": pw_error}), 400

    # Re-authenticate to verify the current password.
    # A fresh client is used so this call doesn't mutate the shared module-level
    # client's session state and cannot interfere with concurrent requests.
    try:
        reauth_client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        reauth_client.auth.sign_in_with_password({"email": user_email, "password": current_password})
    except Exception as exc:
        logger.warning("change_password: current password incorrect for user %s: %s", user_id, exc)
        return jsonify({"error": "Current password is incorrect"}), 401

    # Apply the new password using the same client that just signed in —
    # it has an active internal session, which update_user requires.
    try:
        reauth_client.auth.update_user({"password": new_password})
        logger.info("change_password: password updated for user %s", user_id)
        return jsonify({"success": True}), 200
    except Exception as exc:
        logger.error("change_password: update_user failed for user %s: %s", user_id, exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    Sign out the current user's session.

    Requires: Authorization: Bearer <access_token>
    """
    token, err = _require_token()
    if err:
        return err

    try:
        # Use user-scoped client for the sign-out call
        user_supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_supabase.auth.sign_out()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ---------------------------------------------------------------------------
# Photo upload endpoint
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload_photo():
    """
    Upload an outfit photo to Supabase Storage.

    Requires: Authorization: Bearer <access_token>
    Form data: file=<image file>
    Response JSON: { "path": str, "url": str }
    """
    token, err = _require_token()
    if err:
        return err

    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate MIME type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.mimetype not in allowed_types:
        return jsonify({"error": f"Unsupported file type: {file.mimetype}"}), 415

    try:
        # Build a Supabase client that sends the user's JWT as the Authorization
        # header. This makes Supabase Storage evaluate RLS policies as the
        # authenticated user rather than the anonymous role.
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )

        # Validate the token and retrieve the user ID
        user_resp = user_supabase.auth.get_user(token)
        user_id = user_resp.user.id

        # Build a unique storage path: <user_id>/<filename>
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{user_id}/{unique_filename}"

        file_bytes = file.read()

        # Enforce maximum file size
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            return jsonify({"error": "File too large (maximum 10 MB)"}), 413

        # Upload to Supabase Storage bucket as the authenticated user
        user_supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.mimetype},
        )

        # Get a public URL for the uploaded file
        public_url = user_supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        logger.info("Upload succeeded for user %s: %s", user_id, storage_path)
        return jsonify({"path": storage_path, "url": public_url}), 201

    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Style analysis endpoint (Claude vision)
# ---------------------------------------------------------------------------

@app.route("/api/analyze", methods=["POST"])
def analyze_style():
    """
    Send an uploaded image to Claude for AI style analysis.

    Requires: Authorization: Bearer <access_token>
    Request JSON: { "image_url": str }  OR  form data with file=<image>
    Response JSON:
      {
        "colors": [...],
        "silhouettes": [...],
        "style_tags": [...],
        "summary": str
      }
    """
    token, err = _require_token()
    if err:
        return err

    # Resolve user_id for history persistence — non-fatal if unavailable
    _analysis_user_id = None
    try:
        _user_supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        _user_resp = _user_supabase.auth.get_user(token)
        _analysis_user_id = _user_resp.user.id
    except Exception as _exc:
        logger.warning("analyze_style: could not resolve user_id for history: %s", _exc)

    # Fetch profile for personalised prompt context — non-fatal
    _analysis_profile: dict | None = None
    if _analysis_user_id:
        _analysis_profile = get_user_profile(_analysis_user_id, token)

    # Accept either a URL reference or a direct file upload
    image_bytes = None
    image_url = None
    media_type = "image/jpeg"

    if request.is_json:
        body = request.get_json(silent=True) or {}
        image_url = body.get("image_url", "").strip()
        if not image_url:
            return jsonify({"error": "image_url is required"}), 400

        # Validate the URL to prevent SSRF — returns a reconstructed safe URL
        safe_url, url_error = _safe_image_url(image_url)
        if url_error:
            return jsonify({"error": f"Invalid image_url: {url_error}"}), 400

        # Fetch the image bytes so we can pass them to Claude
        try:
            img_resp = req_lib.get(safe_url, timeout=15)
            img_resp.raise_for_status()
            # Guard against excessively large remote images using the
            # Content-Length header before loading the full response body.
            content_length = int(img_resp.headers.get("Content-Length", 0))
            if content_length > MAX_UPLOAD_BYTES:
                return jsonify({"error": "Remote image too large (maximum 10 MB)"}), 413
            image_bytes = img_resp.content
            if len(image_bytes) > MAX_UPLOAD_BYTES:
                return jsonify({"error": "Remote image too large (maximum 10 MB)"}), 413
            media_type = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
        except req_lib.exceptions.Timeout:
            return jsonify({"error": "Timed out fetching image"}), 408
        except req_lib.exceptions.RequestException as exc:
            return jsonify({"error": f"Failed to fetch image: {exc}"}), 400

    elif "file" in request.files:
        file = request.files["file"]
        image_bytes = file.read()
        media_type = file.mimetype or "image/jpeg"
    else:
        return jsonify({"error": "Provide image_url (JSON) or multipart file"}), 400

    # Compress to under 4.5 MB before base64-encoding for Claude
    image_bytes, media_type = _compress_image_bytes(image_bytes, media_type)
    image_data_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # -----------------------------------------------------------------------
    # Build the Claude prompt
    # -----------------------------------------------------------------------
    _profile_context = ""
    if _analysis_profile:
        parts = []
        if _analysis_profile.get("gender"):
            parts.append(f"gender: {_analysis_profile['gender']}")
        if _analysis_profile.get("age_range"):
            parts.append(f"age range: {_analysis_profile['age_range']}")
        if _analysis_profile.get("preferred_styles"):
            parts.append(f"preferred styles: {', '.join(_analysis_profile['preferred_styles'])}")
        if _analysis_profile.get("occasions"):
            parts.append(f"typical occasions: {', '.join(_analysis_profile['occasions'])}")
        if parts:
            _profile_context = (
                "User context (use this to personalise your analysis): "
                + "; ".join(parts) + ".\n\n"
            )

    system_prompt = (
        _profile_context
        + "You are an expert fashion stylist and personal shopping consultant. "
        "Analyse the clothing/outfit in the provided image and respond ONLY with "
        "valid JSON matching exactly this schema (no markdown fences, no extra keys):\n"
        '{\n'
        '  "colors": ["<color1>", ...],\n'
        '  "silhouettes": ["<silhouette1>", ...],\n'
        '  "style_tags": ["<tag1>", ...],\n'
        '  "summary": "<one-paragraph style summary>"\n'
        '}'
    )

    try:
        message = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Please analyse this outfit image and return the "
                                "structured JSON with colors, silhouettes, style tags, "
                                "and a style summary."
                            ),
                        },
                    ],
                }
            ],
        )

        raw_text = message.content[0].text.strip()

        # Strip any accidental markdown code fences (e.g. ```json ... ```)
        if raw_text.startswith("```"):
            parts = raw_text.split("```")
            if len(parts) >= 2:
                # parts[1] is the content inside the first fence pair
                inner = parts[1]
                if inner.startswith("json"):
                    inner = inner[4:]
                raw_text = inner.strip()

        result = json.loads(raw_text)
        analysis_id = save_analysis(_analysis_user_id, image_url, result, token)
        if analysis_id:
            result["analysis_id"] = analysis_id
        logger.info("Style analysis completed successfully")
        return jsonify(result), 200

    except json.JSONDecodeError:
        # Return the raw text if Claude's response isn't valid JSON
        logger.warning("Claude returned non-JSON response")
        return jsonify({"raw_response": raw_text, "error": "Claude returned non-JSON"}), 502
    except anthropic.APIError as exc:
        logger.error("Claude API error: %s", exc)
        return jsonify({"error": f"Claude API error: {exc}"}), 502
    except Exception as exc:
        logger.error("Unexpected error in analyze_style: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# AI-powered recommendations — helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences from a string before JSON parsing."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()
    return text


def generate_search_queries(
    analysis: dict,
    profile: dict | None = None,
    wardrobe_summary: list[dict] | None = None,
) -> list[str]:
    """
    Ask Claude to produce 4 specific product search queries derived from the
    style analysis and (optionally) the user's profile and wardrobe.
    Returns a list of query strings.
    """
    system = (
        "You are a fashion search specialist. Given a style analysis JSON "
        "(and optional user profile context), generate exactly 4 specific product "
        "search queries that a shopper would type into Google Shopping to find "
        "clothing that matches the style. Be specific — include colors, silhouettes, "
        "and style descriptors. Factor in the user's preferred styles, favourite "
        "brands, occasions, and budget when provided. "
        'Return ONLY valid JSON in the form: {"queries": ["...", "...", "...", "..."]}'
    )
    profile_section = ""
    if profile:
        pf = {}
        for key in ("gender", "age_range", "preferred_styles", "favorite_brands",
                    "occasions", "budget_min_usd", "budget_max_usd"):
            val = profile.get(key)
            if val:
                pf[key] = val
        if pf:
            profile_section = f"\n\nUser profile:\n{json.dumps(pf, indent=2)}"

    wardrobe_section = ""
    if wardrobe_summary:
        wardrobe_section = (
            f"\n\nUser's wardrobe (owned/wishlist items):\n"
            f"{json.dumps(wardrobe_summary[:20], indent=2)}\n\n"
            "Suggest complementary items that pair well with what they own. "
            "Avoid suggesting duplicates of items they already have."
        )

    user_msg = (
        f"Style analysis:\n{json.dumps(analysis, indent=2)}"
        f"{profile_section}"
        f"{wardrobe_section}\n\n"
        "Generate 4 targeted product search queries."
    )
    msg = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        timeout=30,
    )
    parsed = json.loads(_strip_fences(msg.content[0].text))
    return [str(q) for q in parsed.get("queries", [])][:4]


def search_products(query: str) -> list[dict]:
    """
    Call RapidAPI's Real-Time Product Search (/search-v2) for *query* and
    return up to 2 results normalised to {product_id, title, price, image_url,
    product_url, retailer, source_query}.  Returns [] on any failure.

    Products missing required fields (title or product_url) are skipped rather
    than causing the whole call to fail.
    """
    url = f"https://{RAPIDAPI_HOST}/search-v2"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    params = {
        "q": query,
        "page": "1",
        "sort_by": "BEST_MATCH",
        "product_condition": "ANY",
        "return_filters": "false",
    }

    try:
        resp = req_lib.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("search_products failed for query '%s': %s", query, exc)
        return []

    raw: list = data.get("data", {}).get("products", []) if isinstance(data, dict) else []

    results: list[dict] = []
    for item in raw:
        if len(results) >= 2:
            break

        offer = item.get("offer") or {}

        title = item.get("product_title") or ""
        product_url = item.get("product_page_url") or offer.get("offer_page_url") or ""

        # Skip products missing the fields a card needs to be useful
        if not title or not product_url:
            continue

        photos = item.get("product_photos") or []
        image_url = photos[0] if photos else ""

        price = str(offer["price"]) if offer.get("price") else ""

        results.append({
            "product_id": item.get("product_id") or "",
            "title": title,
            "price": price,
            "image_url": image_url,
            "product_url": product_url,
            "retailer": offer.get("store_name") or "",
            "source_query": query,
        })

    return results


def annotate_recommendations(
    analysis: dict,
    products: list[dict],
    profile: dict | None = None,
    wardrobe_summary: list[dict] | None = None,
) -> list[dict]:
    """
    Ask Claude to add a why_it_matches field (≤20 words) to each product dict.
    Falls back to returning products unchanged if the Claude call fails.
    """
    if not products:
        return products

    profile_section = ""
    if profile:
        pf = {}
        for key in ("gender", "age_range", "body_type", "preferred_styles", "occasions"):
            val = profile.get(key)
            if val:
                pf[key] = val
        if pf:
            profile_section = f"\n\nUser profile:\n{json.dumps(pf, indent=2)}"

    wardrobe_section = ""
    if wardrobe_summary:
        wardrobe_section = (
            f"\n\nUser's wardrobe (for context — reference items they own where relevant):\n"
            f"{json.dumps(wardrobe_summary[:10], indent=2)}"
        )

    system = (
        "You are a personal stylist. Given a style analysis, optional user profile "
        "context, optional wardrobe context, and a list of products, add a "
        "'why_it_matches' field to each product explaining in ≤20 words why it suits "
        "the style and the user (you may reference wardrobe items it pairs with). "
        "Return ONLY a valid JSON array with the same products plus the "
        "why_it_matches field on each."
    )
    user_msg = (
        f"Style analysis:\n{json.dumps(analysis, indent=2)}"
        f"{profile_section}"
        f"{wardrobe_section}\n\n"
        f"Products:\n{json.dumps(products, indent=2)}\n\n"
        "Add why_it_matches to each product and return the JSON array."
    )

    try:
        msg = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            timeout=30,
        )
        annotated = json.loads(_strip_fences(msg.content[0].text))
        if isinstance(annotated, list) and len(annotated) == len(products):
            return annotated
    except Exception as exc:
        logger.warning("annotate_recommendations failed: %s", exc)

    return products


def _enrich_missing_pieces(
    missing_pieces: list[dict],
    anchor_item: dict,
    profile: dict | None,
) -> list[dict]:
    """
    For each missing piece, search for real products and annotate them.
    Returns a new list where each piece has a 'products' key (may be []).
    Non-fatal: per-piece failures degrade to empty products array.
    """
    if not missing_pieces:
        return missing_pieces

    # Guard: only use profile if it's actually a dict (handles non-fatal None/mock returns)
    if not isinstance(profile, dict):
        profile = None

    budget_suffix = ""
    if profile:
        budget = profile.get("budget_max_usd")
        if budget:
            budget_suffix = f" under ${budget}"

    # Build a lightweight analysis dict from the anchor for annotation context
    anchor_analysis = {
        "colors": anchor_item.get("colors", []),
        "style_tags": anchor_item.get("style_tags", []),
        "summary": anchor_item.get("description", ""),
    }

    enriched: list[dict] = []
    for piece in missing_pieces:
        piece_copy = dict(piece)
        desc = piece.get("description", "")
        query = desc + budget_suffix if desc else (piece.get("role", "") + budget_suffix)
        try:
            products = search_products(query)[:2]
            if products:
                try:
                    products = annotate_recommendations(anchor_analysis, products, profile)
                except Exception as ann_exc:
                    logger.warning("_enrich_missing_pieces: annotation failed: %s", ann_exc)
        except Exception as exc:
            logger.warning("_enrich_missing_pieces: search failed for '%s': %s", query, exc)
            products = []
        piece_copy["products"] = products
        enriched.append(piece_copy)

    return enriched


# ---------------------------------------------------------------------------
# Recommendations endpoints (AI-powered, per analysis)
# ---------------------------------------------------------------------------

@app.route("/api/recommendations/<analysis_id>", methods=["POST"])
def get_recommendations(analysis_id: str):
    """
    Return AI-powered product recommendations for a given style analysis.

    Requires: Authorization: Bearer <access_token>

    1. Returns cached results immediately if available.
    2. Otherwise: fetches the analysis, asks Claude for search queries,
       calls RapidAPI for products, asks Claude to annotate each with
       why_it_matches, caches the results, and returns them.

    Response JSON: { "recommendations": [...], "cached": bool }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_resp = user_supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception as exc:
        logger.warning("get_recommendations: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    # Check cache first
    try:
        cache_resp = (
            user_supabase.table("recommendation_cache")
            .select("recommendations")
            .eq("analysis_id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if cache_resp.data:
            logger.info("Cache hit for analysis %s", analysis_id)
            return jsonify({
                "recommendations": cache_resp.data[0]["recommendations"],
                "cached": True,
            }), 200
    except Exception as exc:
        logger.warning("Cache lookup failed for %s: %s", analysis_id, exc)

    # Cache miss — fetch the style analysis row (RLS ensures ownership)
    try:
        analysis_resp = (
            user_supabase.table("style_analyses")
            .select("colors,silhouettes,style_tags,summary")
            .eq("id", analysis_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to fetch analysis %s: %s", analysis_id, exc)
        return jsonify({"error": "Failed to fetch analysis"}), 500

    if not analysis_resp.data:
        return jsonify({"error": "Analysis not found"}), 404

    analysis = analysis_resp.data[0]

    # Fetch user profile for personalised queries — non-fatal
    profile = get_user_profile(user_id, token)

    # Fetch wardrobe summary for context — non-fatal
    wardrobe_summary = get_wardrobe_summary(user_id, token) or None

    # Generate search queries via Claude (profile-aware, wardrobe-aware)
    try:
        queries = generate_search_queries(analysis, profile, wardrobe_summary)
    except Exception as exc:
        logger.error("generate_search_queries failed: %s", exc)
        return jsonify({"error": "Failed to generate search queries"}), 502

    # Optionally append budget hint to each query
    budget_max = profile.get("budget_max_usd") if profile else None
    if budget_max:
        queries = [f"{q} under ${budget_max}" for q in queries]

    # Fetch products from RapidAPI for each query (failures are skipped)
    all_products: list[dict] = []
    for q in queries:
        all_products.extend(search_products(q))

    if not all_products:
        return jsonify({"recommendations": [], "cached": False}), 200

    # Ask Claude to annotate each product with why_it_matches (profile- and wardrobe-aware)
    annotated = annotate_recommendations(analysis, all_products, profile, wardrobe_summary)

    # Write to cache (non-fatal)
    try:
        user_supabase.table("recommendation_cache").upsert({
            "analysis_id": analysis_id,
            "user_id": user_id,
            "recommendations": annotated,
        }, on_conflict="analysis_id").execute()
        logger.info("Cached %d recommendations for analysis %s", len(annotated), analysis_id)
    except Exception as exc:
        logger.warning("Failed to cache recommendations for %s: %s", analysis_id, exc)

    return jsonify({"recommendations": annotated, "cached": False}), 200


@app.route("/api/recommendations/<analysis_id>", methods=["DELETE"])
def delete_recommendations(analysis_id: str):
    """
    Clear the recommendation cache for a given analysis (force refresh).

    Requires: Authorization: Bearer <access_token>
    Response JSON: { "deleted": true }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_resp = user_supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception as exc:
        logger.warning("delete_recommendations: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        user_supabase.table("recommendation_cache").delete().eq(
            "analysis_id", analysis_id
        ).eq("user_id", user_id).execute()
        logger.info("Cleared recommendation cache for analysis %s", analysis_id)
        return jsonify({"deleted": True}), 200
    except Exception as exc:
        logger.error("delete_recommendations failed for %s: %s", analysis_id, exc)
        return jsonify({"error": "Failed to clear cache"}), 500


# ---------------------------------------------------------------------------
# User profile — field allowlist, helper, and endpoints
# ---------------------------------------------------------------------------

# Maps each writable profile field to its expected Python type.
_PROFILE_FIELDS: dict[str, type] = {
    "gender": str,
    "age_range": str,
    "body_type": str,
    "height_cm": int,
    "weight_kg": int,
    "preferred_styles": list,
    "favorite_brands": list,
    "occasions": list,
    "shirt_size": str,
    "pants_size": str,
    "shoe_size": str,
    "budget_min_usd": int,
    "budget_max_usd": int,
}


def get_user_profile(user_id: str, access_token: str) -> dict | None:
    """
    Fetch the authenticated user's profile row.  Returns the row dict, or
    None if no profile exists or any error occurs.

    Non-fatal by design — callers must degrade gracefully when None is returned.
    """
    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
        )
        resp = (
            user_supabase.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as exc:
        logger.warning("get_user_profile failed for %s: %s", user_id, exc)
        return None


@app.route("/api/profile", methods=["GET"])
def get_profile():
    """
    Return the authenticated user's profile, or {"profile": null} if none exists.

    Requires: Authorization: Bearer <access_token>
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("get_profile: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        resp = (
            user_supabase.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        profile = resp.data[0] if resp.data else None
        return jsonify({"profile": profile}), 200
    except Exception as exc:
        logger.error("get_profile failed for %s: %s", user_id, exc)
        return jsonify({"error": "Failed to retrieve profile"}), 500


@app.route("/api/profile", methods=["PUT"])
def update_profile():
    """
    Upsert the authenticated user's profile.

    Requires: Authorization: Bearer <access_token>
    Request JSON: any subset of profile fields
    Response JSON: { "profile": { ...saved row... } }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("update_profile: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}

    payload: dict = {}
    for field, expected_type in _PROFILE_FIELDS.items():
        if field not in body:
            continue
        value = body[field]
        if value is not None and not isinstance(value, expected_type):
            return jsonify({"error": f"Field '{field}' must be a {expected_type.__name__}"}), 400
        payload[field] = value

    payload["user_id"] = user_id
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        resp = (
            user_supabase.table("user_profiles")
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        saved = resp.data[0] if resp.data else payload
        logger.info("Profile upserted for user %s", user_id)
        return jsonify({"profile": saved}), 200
    except Exception as exc:
        logger.error("update_profile failed for %s: %s", user_id, exc)
        return jsonify({"error": "Failed to save profile"}), 500


# ---------------------------------------------------------------------------
# Style history endpoint
# ---------------------------------------------------------------------------

@app.route("/api/history", methods=["GET"])
def history():
    """
    Return the authenticated user's past style analyses, newest first.

    Requires: Authorization: Bearer <access_token>
    Response JSON: { "analyses": [ { id, user_id, image_url, colors,
                                      silhouettes, style_tags, summary,
                                      created_at }, ... ] }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_resp = user_supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception as exc:
        logger.warning("history: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        resp = (
            user_supabase.table("style_analyses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        analyses = resp.data if resp.data else []
        return jsonify({"analyses": analyses}), 200
    except Exception as exc:
        logger.error("history query failed for user %s: %s", user_id, exc)
        return jsonify({"error": "Failed to retrieve history"}), 500


@app.route("/api/history/<analysis_id>", methods=["DELETE"])
def delete_history_item(analysis_id: str):
    """
    Delete a single style analysis owned by the authenticated user.

    Requires: Authorization: Bearer <access_token>
    Response JSON: { "deleted": true }  (200)  or  { "error": "..." }  (404/401/500)

    The per-request Supabase client carries the user's JWT so RLS ensures
    only the row's owner can delete it (auth.uid() = user_id).
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_resp = user_supabase.auth.get_user(token)
        user_id = user_resp.user.id
    except Exception as exc:
        logger.warning("delete_history_item: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        resp = (
            user_supabase.table("style_analyses")
            .delete()
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not resp.data:
            return jsonify({"error": "Analysis not found"}), 404
        logger.info("Deleted analysis %s for user %s", analysis_id, user_id)
        return jsonify({"deleted": True}), 200
    except Exception as exc:
        logger.error("delete_history_item failed for %s: %s", analysis_id, exc)
        return jsonify({"error": "Failed to delete analysis"}), 500


# ---------------------------------------------------------------------------
# Wardrobe — constants, helpers, and CRUD endpoints
# ---------------------------------------------------------------------------

_WARDROBE_CATEGORIES = {"top", "bottom", "shoes", "outerwear", "accessory"}
_WARDROBE_OWNERSHIP_VALUES = {"owned", "wishlist"}

_WARDROBE_PATCH_FIELDS: dict[str, type] = {
    "category": str,
    "colors": list,
    "style_tags": list,
    "description": str,
    "user_notes": str,
    "ownership": str,
}


def _storage_path_from_url(url: str, bucket: str) -> str | None:
    """Extract the object storage path from a Supabase public URL."""
    marker = f"/storage/v1/object/public/{bucket}/"
    idx = url.find(marker)
    if idx == -1:
        return None
    return url[idx + len(marker):]


def tag_wardrobe_item(image_bytes: bytes, media_type: str) -> dict:
    """
    Ask Claude to identify the clothing item in the image.
    Returns dict with category, colors, style_tags, description.
    Raises on failure — caller handles per-item try/except.
    """
    compressed, compressed_type = _compress_image_bytes(image_bytes, media_type)
    image_data_b64 = base64.standard_b64encode(compressed).decode("utf-8")
    system = (
        "You are a fashion expert. Analyse the single clothing item in the image and "
        "respond ONLY with valid JSON matching exactly this schema (no markdown fences, "
        "no extra keys):\n"
        '{\n'
        '  "category": "<one of: top, bottom, shoes, outerwear, accessory>",\n'
        '  "colors": ["<color1>", ...],\n'
        '  "style_tags": ["<tag1>", ...],\n'
        '  "description": "<one concise sentence describing the item>"\n'
        '}'
    )
    msg = anthropic_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=256,
        system=system,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": compressed_type,
                        "data": image_data_b64,
                    },
                },
                {"type": "text", "text": "Identify this clothing item and return the JSON."},
            ],
        }],
        timeout=30,
    )
    return json.loads(_strip_fences(msg.content[0].text))


def get_wardrobe_summary(user_id: str, access_token: str, limit: int = 30) -> list[dict]:
    """
    Fetch a compact wardrobe summary for AI prompt context.
    Non-fatal: returns [] on any error or when resp.data is not a list.
    """
    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {access_token}"}),
        )
        resp = (
            user_supabase.table("wardrobe_items")
            .select("category,colors,style_tags,ownership")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        if not isinstance(resp.data, list):
            return []
        return [
            {
                "category": item.get("category"),
                "colors": item.get("colors", []),
                "style_tags": item.get("style_tags", []),
                "ownership": item.get("ownership"),
            }
            for item in resp.data
            if isinstance(item, dict)
        ]
    except Exception as exc:
        logger.warning("get_wardrobe_summary failed for %s: %s", user_id, exc)
        return []


@app.route("/api/wardrobe/upload", methods=["POST"])
def wardrobe_upload():
    """
    Upload one or more clothing item photos and auto-tag them with Claude.

    Requires: Authorization: Bearer <access_token>
    Form data: files=<image> (repeatable), ownership=owned|wishlist
    Response JSON: { "items": [...], "failures": [...] }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("wardrobe_upload: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    ownership = request.form.get("ownership", "owned")
    if ownership not in _WARDROBE_OWNERSHIP_VALUES:
        return jsonify({"error": "ownership must be 'owned' or 'wishlist'"}), 400

    files = request.files.getlist("files")
    files = [f for f in files if f.filename]
    if not files:
        return jsonify({"error": "No files provided"}), 400

    results: list[dict] = []
    failures: list[dict] = []

    for file in files:
        filename = file.filename or "upload"
        try:
            if not (file.mimetype or "").startswith("image/"):
                failures.append({"filename": filename, "error": f"Unsupported type: {file.mimetype}"})
                continue

            file_bytes = file.read()
            if len(file_bytes) > MAX_UPLOAD_BYTES:
                failures.append({"filename": filename, "error": "File too large (maximum 10 MB)"})
                continue

            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
            storage_path = f"{user_id}/{uuid.uuid4()}.{ext}"
            user_supabase.storage.from_(WARDROBE_BUCKET).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.mimetype},
            )
            image_url = user_supabase.storage.from_(WARDROBE_BUCKET).get_public_url(storage_path)

            tags = tag_wardrobe_item(file_bytes, file.mimetype or "image/jpeg")

            category = tags.get("category", "")
            if category not in _WARDROBE_CATEGORIES:
                category = None

            insert_resp = user_supabase.table("wardrobe_items").insert({
                "user_id": user_id,
                "image_url": image_url,
                "ownership": ownership,
                "category": category,
                "colors": tags.get("colors", []),
                "style_tags": tags.get("style_tags", []),
                "description": tags.get("description", ""),
            }).execute()

            if insert_resp.data:
                results.append(insert_resp.data[0])
                logger.info("Wardrobe item uploaded for user %s: %s", user_id, storage_path)
            else:
                failures.append({"filename": filename, "error": "Insert returned no data"})

        except Exception as exc:
            logger.error("wardrobe_upload failed for '%s': %s", filename, exc)
            failures.append({"filename": filename, "error": str(exc)})

    if not results:
        return jsonify({"error": "All uploads failed", "failures": failures}), 500

    return jsonify({"items": results, "failures": failures}), 201


@app.route("/api/wardrobe", methods=["GET"])
def list_wardrobe():
    """
    Return the authenticated user's wardrobe items, newest first.

    Requires: Authorization: Bearer <access_token>
    Query params: ?ownership=owned|wishlist (optional)
    Response JSON: { "items": [...] }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("list_wardrobe: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    ownership_filter = request.args.get("ownership")

    try:
        query = (
            user_supabase.table("wardrobe_items")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(200)
        )
        if ownership_filter in _WARDROBE_OWNERSHIP_VALUES:
            query = query.eq("ownership", ownership_filter)
        resp = query.execute()
        return jsonify({"items": resp.data or []}), 200
    except Exception as exc:
        logger.error("list_wardrobe failed for user %s: %s", user_id, exc)
        return jsonify({"error": "Failed to retrieve wardrobe"}), 500


@app.route("/api/wardrobe/<item_id>", methods=["PATCH"])
def patch_wardrobe_item(item_id: str):
    """
    Update editable fields on a wardrobe item.

    Requires: Authorization: Bearer <access_token>
    Request JSON: any subset of category, colors, style_tags, description,
                  user_notes, ownership
    Response JSON: { "item": { ...updated row... } }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("patch_wardrobe_item: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}
    payload: dict = {}

    for field, expected_type in _WARDROBE_PATCH_FIELDS.items():
        if field not in body:
            continue
        value = body[field]
        if value is not None and not isinstance(value, expected_type):
            return jsonify({"error": f"Field '{field}' must be a {expected_type.__name__}"}), 400
        if field == "ownership" and value not in _WARDROBE_OWNERSHIP_VALUES:
            return jsonify({"error": "ownership must be 'owned' or 'wishlist'"}), 400
        payload[field] = value

    if not payload:
        return jsonify({"error": "No valid fields to update"}), 400

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        resp = (
            user_supabase.table("wardrobe_items")
            .update(payload)
            .eq("id", item_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not resp.data:
            return jsonify({"error": "Item not found"}), 404
        return jsonify({"item": resp.data[0]}), 200
    except Exception as exc:
        logger.error("patch_wardrobe_item failed for %s: %s", item_id, exc)
        return jsonify({"error": "Failed to update item"}), 500


@app.route("/api/wardrobe/<item_id>", methods=["DELETE"])
def delete_wardrobe_item(item_id: str):
    """
    Delete a wardrobe item row and its storage image (best-effort).

    Requires: Authorization: Bearer <access_token>
    Response JSON: { "deleted": true }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("delete_wardrobe_item: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        resp = (
            user_supabase.table("wardrobe_items")
            .delete()
            .eq("id", item_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not resp.data:
            return jsonify({"error": "Item not found"}), 404

        # Best-effort storage deletion
        try:
            image_url = resp.data[0].get("image_url", "")
            storage_path = _storage_path_from_url(image_url, WARDROBE_BUCKET)
            if storage_path:
                user_supabase.storage.from_(WARDROBE_BUCKET).remove([storage_path])
                logger.info("Deleted wardrobe storage object: %s", storage_path)
        except Exception as storage_exc:
            logger.warning("Failed to delete storage object for item %s: %s", item_id, storage_exc)

        logger.info("Deleted wardrobe item %s for user %s", item_id, user_id)
        return jsonify({"deleted": True}), 200
    except Exception as exc:
        logger.error("delete_wardrobe_item failed for %s: %s", item_id, exc)
        return jsonify({"error": "Failed to delete item"}), 500


@app.route("/api/wardrobe/derive-style", methods=["POST"])
def derive_style_from_wardrobe():
    """
    Analyse the user's wardrobe and derive style preferences via Claude.

    Requires: Authorization: Bearer <access_token>
    Response JSON: { "preferred_styles": [...], "color_palette": [...],
                     "style_summary": "..." }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("derive_style_from_wardrobe: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    try:
        resp = (
            user_supabase.table("wardrobe_items")
            .select("category,colors,style_tags,description,ownership")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        items = resp.data or []
    except Exception as exc:
        logger.error("derive_style_from_wardrobe: fetch failed: %s", exc)
        return jsonify({"error": "Failed to fetch wardrobe"}), 500

    if len(items) < 5:
        return jsonify({
            "error": "Please add at least 5 items to your wardrobe before deriving your style."
        }), 400

    summary = [
        {
            "category": item.get("category"),
            "colors": item.get("colors", []),
            "style_tags": item.get("style_tags", []),
            "description": item.get("description", ""),
            "ownership": item.get("ownership"),
        }
        for item in items
        if isinstance(item, dict)
    ]

    system = (
        "You are a personal stylist. Analyse the user's wardrobe and identify their "
        "style DNA. Return ONLY valid JSON with exactly this schema (no markdown fences, "
        "no extra keys):\n"
        '{\n'
        '  "preferred_styles": ["<style1>", ...],\n'
        '  "color_palette": ["<color1>", ...],\n'
        '  "style_summary": "<2-3 sentence written style summary>"\n'
        '}'
    )
    user_msg = (
        f"Wardrobe ({len(summary)} items):\n{json.dumps(summary, indent=2)}\n\n"
        "Identify dominant preferred styles, common colour palette, and write a style summary."
    )

    try:
        msg = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            timeout=30,
        )
        result = json.loads(_strip_fences(msg.content[0].text))
        return jsonify(result), 200
    except json.JSONDecodeError:
        return jsonify({"error": "Claude returned non-JSON response"}), 502
    except anthropic.APIError as exc:
        logger.error("derive_style_from_wardrobe: Claude API error: %s", exc)
        return jsonify({"error": f"Claude API error: {exc}"}), 502
    except Exception as exc:
        logger.error("derive_style_from_wardrobe failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/wardrobe/build-outfit", methods=["POST"])
def build_outfit():
    """
    Build a complete outfit around a single anchor wardrobe item using Claude.

    Claude selects complementary pieces from the rest of the user's wardrobe where
    possible, and identifies any gaps that cannot be filled from existing items.

    Requires: Authorization: Bearer <access_token>
    Request JSON: { "anchor_item_id": "<uuid>", "occasion": "..." (optional) }
    Response JSON:
      {
        "anchor_item_id": "...",
        "summary": "...",
        "wardrobe_pieces": [
          { "item_id": "<uuid>", "role": "top|bottom|shoes|outerwear|accessory",
            "reason": "why it works with the anchor" }
        ],
        "missing_pieces": [
          { "role": "shoes", "description": "white low-top sneakers would complete this" }
        ]
      }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("build_outfit: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}
    anchor_item_id = body.get("anchor_item_id", "")
    occasion = body.get("occasion", "")

    if not anchor_item_id or not isinstance(anchor_item_id, str):
        return jsonify({"error": "anchor_item_id is required"}), 400

    # Fetch the anchor item — RLS plus explicit user_id check ensures ownership
    try:
        anchor_resp = (
            user_supabase.table("wardrobe_items")
            .select("*")
            .eq("id", anchor_item_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("build_outfit: failed to fetch anchor item: %s", exc)
        return jsonify({"error": "Failed to fetch wardrobe item"}), 500

    if not anchor_resp.data:
        return jsonify({"error": "Anchor item not found"}), 404

    anchor_item = anchor_resp.data[0]

    # Fetch the rest of the wardrobe (exclude anchor) — non-fatal
    try:
        rest_resp = (
            user_supabase.table("wardrobe_items")
            .select("id,category,colors,style_tags,description,ownership")
            .eq("user_id", user_id)
            .neq("id", anchor_item_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        other_items = rest_resp.data if isinstance(rest_resp.data, list) else []
    except Exception as exc:
        logger.warning("build_outfit: failed to fetch rest of wardrobe: %s", exc)
        other_items = []

    # Fetch user profile for context — non-fatal
    profile = get_user_profile(user_id, token)
    profile_context = ""
    if profile:
        parts = []
        for key in ("gender", "age_range", "body_type", "preferred_styles", "occasions"):
            val = profile.get(key)
            if val:
                parts.append(f"{key}: {val}")
        if parts:
            profile_context = "\n\nUser profile: " + "; ".join(parts) + "."

    system = (
        "You are a personal stylist. Build a complete outfit around the anchor item "
        "by selecting complementary pieces from the user's wardrobe where possible. "
        "Return ONLY valid JSON with exactly this schema (no markdown fences, no extra keys):\n"
        '{\n'
        '  "anchor_item_id": "<same UUID as the anchor>",\n'
        '  "summary": "<2-3 sentence outfit description and why it works>",\n'
        '  "wardrobe_pieces": [\n'
        '    { "item_id": "<UUID from available wardrobe>", "role": "<top|bottom|shoes|outerwear|accessory>", "reason": "<one sentence why>" }\n'
        '  ],\n'
        '  "missing_pieces": [\n'
        '    { "role": "<category>", "description": "<type of item needed>" }\n'
        '  ]\n'
        '}\n'
        "Rules:\n"
        "- Only add wardrobe_pieces for items that genuinely complement the anchor.\n"
        "- Only add missing_pieces for gaps you cannot fill from the available wardrobe.\n"
        "- Aim for a complete, wearable outfit (typically top + bottom + shoes, plus any fitting outerwear/accessories).\n"
        "- Do not include the anchor item itself in wardrobe_pieces."
    )

    anchor_display = {
        "id": anchor_item.get("id"),
        "category": anchor_item.get("category"),
        "colors": anchor_item.get("colors", []),
        "style_tags": anchor_item.get("style_tags", []),
        "description": anchor_item.get("description", ""),
        "ownership": anchor_item.get("ownership"),
    }
    occasion_context = f"\nOccasion: {occasion}" if occasion else ""
    user_msg = (
        f"Anchor item (build the outfit around this):\n{json.dumps(anchor_display, indent=2)}"
        f"{occasion_context}"
        f"{profile_context}\n\n"
        f"Available wardrobe items:\n{json.dumps(other_items, indent=2)}"
    )

    try:
        msg = anthropic_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            timeout=30,
        )
        result = json.loads(_strip_fences(msg.content[0].text))
    except json.JSONDecodeError:
        return jsonify({"error": "Claude returned non-JSON response"}), 502
    except anthropic.APIError as exc:
        logger.error("build_outfit: Claude API error: %s", exc)
        return jsonify({"error": f"Claude API error: {exc}"}), 502
    except Exception as exc:
        logger.error("build_outfit failed: %s", exc)
        return jsonify({"error": str(exc)}), 500

    # Enrich missing pieces with real product search results (non-fatal)
    if result.get("missing_pieces"):
        result["missing_pieces"] = _enrich_missing_pieces(
            result["missing_pieces"], anchor_item, profile
        )

    return jsonify(result), 200


@app.route("/api/profile/apply-derived", methods=["POST"])
def apply_derived_profile():
    """
    Merge derived style suggestions into the user's existing profile.

    Array fields are unioned (no duplicates); string fields are only set if
    the existing value is empty.

    Requires: Authorization: Bearer <access_token>
    Request JSON: any subset of profile fields (same allowlist as PUT /api/profile)
    Response JSON: { "profile": { ...updated row... } }
    """
    token, err = _require_token()
    if err:
        return err

    try:
        user_supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(headers={"Authorization": f"Bearer {token}"}),
        )
        user_id = user_supabase.auth.get_user(token).user.id
    except Exception as exc:
        logger.warning("apply_derived_profile: token validation failed: %s", exc)
        return jsonify({"error": "Invalid or expired token"}), 401

    body = request.get_json(silent=True) or {}

    incoming: dict = {}
    for field, expected_type in _PROFILE_FIELDS.items():
        if field not in body:
            continue
        value = body[field]
        if value is not None and not isinstance(value, expected_type):
            return jsonify({"error": f"Field '{field}' must be a {expected_type.__name__}"}), 400
        incoming[field] = value

    if not incoming:
        return jsonify({"error": "No valid profile fields provided"}), 400

    existing = get_user_profile(user_id, token) or {}

    merged: dict = dict(existing)
    for field, new_val in incoming.items():
        existing_val = existing.get(field)
        if isinstance(new_val, list):
            existing_list = existing_val if isinstance(existing_val, list) else []
            merged[field] = list(dict.fromkeys(existing_list + new_val))
        elif isinstance(new_val, str):
            if not existing_val:
                merged[field] = new_val
        else:
            merged[field] = new_val

    merged["user_id"] = user_id
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()

    allowed_keys = set(_PROFILE_FIELDS.keys()) | {"user_id", "updated_at"}
    merged = {k: v for k, v in merged.items() if k in allowed_keys}

    try:
        resp = (
            user_supabase.table("user_profiles")
            .upsert(merged, on_conflict="user_id")
            .execute()
        )
        saved = resp.data[0] if resp.data else merged
        logger.info("apply_derived_profile upserted for user %s", user_id)
        return jsonify({"profile": saved}), 200
    except Exception as exc:
        logger.error("apply_derived_profile failed for %s: %s", user_id, exc)
        return jsonify({"error": "Failed to apply derived profile"}), 500


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok"}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug_mode)
