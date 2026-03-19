"""
AI-Powered Personal Style Assistant — Flask Backend
Provides RESTful API endpoints for user auth, photo upload,
AI style analysis via Claude, and style-based recommendations.
"""

import logging
import os
import re
import uuid
import base64
import json
from urllib.parse import urlparse

import requests as req_lib

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client

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

_REQUIRED_ENV_VARS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "ANTHROPIC_API_KEY")
_missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Please check your .env file."
    )

app = Flask(__name__)

# Allow requests from the React dev server (and any deployed origin).
# In production, restrict CORS_ORIGINS to your actual domain.
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})

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

# Storage bucket for outfit photos
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "outfit-photos")

# Maximum allowed upload size (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

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
# Auth endpoints
# ---------------------------------------------------------------------------

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
        # Retrieve user ID from Supabase using the access token
        user_supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
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

        # Upload to Supabase Storage bucket
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.mimetype},
        )

        # Get a public URL for the uploaded file
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

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

    # Accept either a URL reference or a direct file upload
    image_data_b64 = None
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

        image_data_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    elif "file" in request.files:
        file = request.files["file"]
        image_data_b64 = base64.standard_b64encode(file.read()).decode("utf-8")
        media_type = file.mimetype or "image/jpeg"
    else:
        return jsonify({"error": "Provide image_url (JSON) or multipart file"}), 400

    # -----------------------------------------------------------------------
    # Build the Claude prompt
    # -----------------------------------------------------------------------
    system_prompt = (
        "You are an expert fashion stylist and personal shopping consultant. "
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
# Recommendations endpoint
# ---------------------------------------------------------------------------

# Static curated recommendations keyed by style tag.
# In production these would come from a live web-search / affiliate API.
RECOMMENDATIONS_DB: dict[str, list[dict]] = {
    "casual": [
        {
            "name": "Classic White T-Shirt",
            "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400",
            "price": "$25",
            "link": "https://www.uniqlo.com",
        },
        {
            "name": "Slim-Fit Chinos",
            "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400",
            "price": "$45",
            "link": "https://www.gap.com",
        },
    ],
    "streetwear": [
        {
            "name": "Oversized Graphic Hoodie",
            "image": "https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=400",
            "price": "$65",
            "link": "https://www.hm.com",
        },
        {
            "name": "Cargo Joggers",
            "image": "https://images.unsplash.com/photo-1612810806695-30f7a8258391?w=400",
            "price": "$55",
            "link": "https://www.asos.com",
        },
    ],
    "formal": [
        {
            "name": "Tailored Blazer",
            "image": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=400",
            "price": "$120",
            "link": "https://www.zara.com",
        },
        {
            "name": "Dress Shirt",
            "image": "https://images.unsplash.com/photo-1620012253295-c15cc3e65df4?w=400",
            "price": "$50",
            "link": "https://www.nordstrom.com",
        },
    ],
    "minimalist": [
        {
            "name": "Clean-Cut Trousers",
            "image": "https://images.unsplash.com/photo-1594938298603-c8148c4b4e3b?w=400",
            "price": "$70",
            "link": "https://www.cos.com",
        },
        {
            "name": "Ribbed Turtleneck",
            "image": "https://images.unsplash.com/photo-1608234807905-4466023792f5?w=400",
            "price": "$55",
            "link": "https://www.arket.com",
        },
    ],
    "bohemian": [
        {
            "name": "Floral Midi Dress",
            "image": "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?w=400",
            "price": "$80",
            "link": "https://www.freepeople.com",
        },
        {
            "name": "Woven Belt Bag",
            "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400",
            "price": "$35",
            "link": "https://www.anthropologie.com",
        },
    ],
    "sporty": [
        {
            "name": "Performance Leggings",
            "image": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400",
            "price": "$60",
            "link": "https://www.nike.com",
        },
        {
            "name": "Athletic Crop Top",
            "image": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400",
            "price": "$40",
            "link": "https://www.adidas.com",
        },
    ],
}

# Default recommendations shown when no recognised style tags are present
DEFAULT_RECOMMENDATIONS = [
    {
        "name": "White Button-Down Shirt",
        "image": "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=400",
        "price": "$40",
        "link": "https://www.everlane.com",
    },
    {
        "name": "Dark Wash Jeans",
        "image": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=400",
        "price": "$60",
        "link": "https://www.levis.com",
    },
    {
        "name": "Leather Sneakers",
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400",
        "price": "$90",
        "link": "https://www.allbirds.com",
    },
]


@app.route("/api/recommendations", methods=["GET", "POST"])
def recommendations():
    """
    Return clothing recommendations based on the user's style tags.

    Requires: Authorization: Bearer <access_token>

    GET  — returns default recommendations
    POST — Request JSON: { "style_tags": ["casual", "minimalist", ...] }
           Response JSON: { "recommendations": [ {name, image, price, link}, ... ] }
    """
    token, err = _require_token()
    if err:
        return err

    style_tags: list[str] = []
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        style_tags = [tag.lower() for tag in body.get("style_tags", [])]

    matched: list[dict] = []
    seen_names: set[str] = set()

    for tag in style_tags:
        for item in RECOMMENDATIONS_DB.get(tag, []):
            if item["name"] not in seen_names:
                matched.append(item)
                seen_names.add(item["name"])

    # Fall back to default items when no tags match
    if not matched:
        matched = DEFAULT_RECOMMENDATIONS

    return jsonify({"recommendations": matched}), 200


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
