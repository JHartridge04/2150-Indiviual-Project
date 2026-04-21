"""
tests/test_app.py
Basic unit tests for the Flask backend.

These tests mock external services (Supabase, Claude) so no real API keys
are required.  Run with:  pytest tests/
"""

import base64
import json
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers — build a fake-but-structurally-valid Supabase anon key (JWT)
# ---------------------------------------------------------------------------

def _fake_jwt() -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": "anon", "iat": 1, "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


FAKE_JWT = _fake_jwt()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    """Create a Flask test client with all external calls mocked."""

    # Provide env vars before the module is imported
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", FAKE_JWT)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("RAPIDAPI_KEY", "fake-rapidapi-key")

    # Patch supabase.create_client so no network call is made at import time
    mock_supabase = MagicMock()
    with patch("supabase.create_client", return_value=mock_supabase):
        # Also patch anthropic.Anthropic so no network call is made
        mock_anthropic = MagicMock()
        with patch("anthropic.Anthropic", return_value=mock_anthropic):
            import importlib
            import sys
            # Force a fresh import of app
            if "app" in sys.modules:
                del sys.modules["app"]
            import app as flask_app
            flask_app.app.config["TESTING"] = True
            with flask_app.app.test_client() as c:
                yield c, mock_supabase, mock_anthropic


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health(client):
    c, *_ = client
    resp = c.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Auth — signup
# ---------------------------------------------------------------------------

def test_signup_missing_fields(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/signup",
        json={"email": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_signup_success(client):
    c, mock_supabase, _ = client

    # Mock the Supabase sign_up response
    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user-123", "email": "test@example.com"}
    mock_session = MagicMock()
    mock_session.model_dump.return_value = {"access_token": "abc", "token_type": "bearer"}
    mock_supabase.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)

    resp = c.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# Auth — change-password
# ---------------------------------------------------------------------------

def test_change_password_requires_auth(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass1", "new_password": "newpass1"},
    )
    assert resp.status_code == 401


def test_change_password_wrong_current(client):
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_user_resp.user.email = "user@example.com"
    mock_supabase.auth.get_user.return_value = mock_user_resp
    mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")

    resp = c.post(
        "/api/auth/change-password",
        json={"current_password": "wrongpass1", "new_password": "newpass12"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.get_json()["error"].lower()


def test_change_password_invalid_new(client):
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_user_resp.user.email = "user@example.com"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    for bad_pw in ("short1", "nonnumber", "12345678"):
        resp = c.post(
            "/api/auth/change-password",
            json={"current_password": "oldpass1", "new_password": bad_pw},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )
        assert resp.status_code == 400, f"Expected 400 for password: {bad_pw!r}"
        assert "error" in resp.get_json()


def test_change_password_success(client):
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_user_resp.user.email = "user@example.com"
    mock_supabase.auth.get_user.return_value = mock_user_resp
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock()
    mock_supabase.auth.update_user.return_value = MagicMock()

    resp = c.post(
        "/api/auth/change-password",
        json={"current_password": "oldpass1", "new_password": "newpass12"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


# ---------------------------------------------------------------------------
# Auth — login
# ---------------------------------------------------------------------------

def test_login_missing_fields(client):
    c, *_ = client
    resp = c.post("/api/auth/login", json={})
    assert resp.status_code == 400


def test_login_success(client):
    c, mock_supabase, _ = client

    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user-123", "email": "test@example.com"}
    mock_session = MagicMock()
    mock_session.model_dump.return_value = {"access_token": "tok", "token_type": "bearer"}
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        user=mock_user, session=mock_session
    )

    resp = c.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Upload — auth guard
# ---------------------------------------------------------------------------

def test_upload_requires_auth(client):
    c, *_ = client
    resp = c.post("/api/upload")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def test_recommendations_requires_auth(client):
    """POST /api/recommendations/<id> with no token must return 401."""
    c, *_ = client
    resp = c.post("/api/recommendations/some-analysis-id")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth — logout
# ---------------------------------------------------------------------------

def test_logout_requires_auth(client):
    c, *_ = client
    resp = c.post("/api/auth/logout")
    assert resp.status_code == 401


def test_logout_success(client):
    c, mock_supabase, _ = client

    resp = c.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "Logged out successfully"


# ---------------------------------------------------------------------------
# Auth — login returns session token
# ---------------------------------------------------------------------------

def test_login_returns_session_token(client):
    c, mock_supabase, _ = client

    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user-123", "email": "test@example.com"}
    mock_session = MagicMock()
    mock_session.model_dump.return_value = {
        "access_token": "valid-token-abc",
        "token_type": "bearer",
    }
    mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
        user=mock_user, session=mock_session
    )

    resp = c.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["session"]["access_token"] == "valid-token-abc"
    assert body["user"] is not None


# ---------------------------------------------------------------------------
# Upload — with file
# ---------------------------------------------------------------------------

def test_upload_success(client):
    c, mock_supabase, _ = client
    import io

    # Mock get_user for token validation
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Mock storage upload and public URL
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.get_public_url.return_value = (
        "https://fake.supabase.co/storage/v1/object/public/outfit-photos/user-123/test.jpg"
    )

    data = {"file": (io.BytesIO(b"fake-image-bytes"), "test.jpg", "image/jpeg")}
    resp = c.post(
        "/api/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert "url" in body
    assert "path" in body


def test_upload_rejects_non_image(client):
    c, mock_supabase, _ = client
    import io

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    data = {"file": (io.BytesIO(b"not-an-image"), "test.txt", "text/plain")}
    resp = c.post(
        "/api/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 415


def test_upload_no_file(client):
    c, *_ = client
    resp = c.post(
        "/api/upload",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Style analysis — Claude API
# ---------------------------------------------------------------------------

def test_analyze_requires_auth(client):
    c, *_ = client
    resp = c.post("/api/analyze", json={"image_url": "https://example.com/img.jpg"})
    assert resp.status_code == 401


def test_analyze_returns_structured_data(client):
    c, mock_supabase, mock_anthropic = client

    # Mock Claude response with structured JSON
    claude_response = MagicMock()
    claude_response.content = [MagicMock()]
    claude_response.content[0].text = json.dumps({
        "colors": ["navy", "white"],
        "silhouettes": ["slim-fit", "tapered"],
        "style_tags": ["casual", "minimalist"],
        "summary": "A clean, understated look with navy and white tones."
    })
    mock_anthropic.messages.create.return_value = claude_response

    # We need to patch the anthropic_client in the app module
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    # Make the insert chain return a real UUID so analysis_id is JSON-serialisable
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "00000000-0000-0000-0000-000000000001"}]
    )

    # Mock the image fetch (since analyze fetches image bytes from URL)
    mock_img_response = MagicMock()
    mock_img_response.content = b"fake-image-bytes"
    mock_img_response.headers = {"Content-Type": "image/jpeg"}
    mock_img_response.raise_for_status.return_value = None

    # Patch get_user_profile so the profile-context building receives None
    # rather than a MagicMock that would make json.dumps fail downstream.
    with patch.object(flask_app, "get_user_profile", return_value=None), \
         patch.object(flask_app.req_lib, "get", return_value=mock_img_response):
        resp = c.post(
            "/api/analyze",
            json={"image_url": "https://fake.supabase.co/storage/v1/object/public/img.jpg"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "colors" in body
    assert "silhouettes" in body
    assert "style_tags" in body
    assert "summary" in body
    assert len(body["colors"]) == 2
    assert "casual" in body["style_tags"]


def test_analyze_handles_claude_error(client):
    c, mock_supabase, mock_anthropic = client
    import anthropic as anthropic_mod

    # Make Claude raise an API error
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)
    mock_anthropic.messages.create.side_effect = anthropic_mod.APIError(
        message="Rate limited",
        request=MagicMock(),
        body=None,
    )

    mock_img_response = MagicMock()
    mock_img_response.content = b"fake-image-bytes"
    mock_img_response.headers = {"Content-Type": "image/jpeg"}
    mock_img_response.raise_for_status.return_value = None

    with patch.object(flask_app.req_lib, "get", return_value=mock_img_response):
        resp = c.post(
            "/api/analyze",
            json={"image_url": "https://fake.supabase.co/storage/v1/object/public/img.jpg"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 502
    body = resp.get_json()
    assert "error" in body


def test_analyze_rejects_non_supabase_url(client):
    c, *_ = client

    resp = c.post(
        "/api/analyze",
        json={"image_url": "https://evil.com/steal-data"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


# ---------------------------------------------------------------------------
# Recommendations — AI-powered endpoint
# ---------------------------------------------------------------------------

ANALYSIS_ID = "aa000000-0000-0000-0000-000000000001"

_FAKE_ANALYSIS_ROW = {
    "colors": ["navy", "white"],
    "silhouettes": ["slim-fit"],
    "style_tags": ["casual", "minimalist"],
    "summary": "Clean navy and white look.",
}

_FAKE_PRODUCTS = [
    {
        "product_id": "p1",
        "title": "Navy Slim Chinos",
        "price": "$55",
        "image_url": "https://example.com/p1.jpg",
        "product_url": "https://example.com/p1",
        "retailer": "Gap",
        "source_query": "navy slim chinos",
        "why_it_matches": "Slim silhouette matches your minimalist navy palette.",
    }
]


def _mock_user(mock_supabase):
    """Wire mock_supabase.auth.get_user to return user-123."""
    u = MagicMock()
    u.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = u


def _chain(*methods):
    """Build a fluent MagicMock chain where every listed method returns self."""
    m = MagicMock()
    for method in methods:
        getattr(m, method).return_value = m
    return m


def test_recommendations_cache_hit(client):
    """Cache hit: returns stored data immediately without calling Claude/RapidAPI."""
    c, mock_supabase, _ = client
    _mock_user(mock_supabase)

    cache_chain = _chain("select", "eq", "limit")
    cache_chain.execute.return_value = MagicMock(data=[{"recommendations": _FAKE_PRODUCTS}])
    mock_supabase.table.return_value = cache_chain

    resp = c.post(
        f"/api/recommendations/{ANALYSIS_ID}",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["cached"] is True
    assert body["recommendations"] == _FAKE_PRODUCTS


def test_recommendations_cache_miss_calls_claude_and_rapidapi(client):
    """Cache miss: fetches analysis, calls Claude for queries, RapidAPI for products."""
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)
    _mock_user(mock_supabase)

    # table() side_effect: return different chains per table name
    cache_chain = _chain("select", "eq", "limit")
    cache_chain.execute.return_value = MagicMock(data=[])  # cache miss

    analysis_chain = _chain("select", "eq", "limit")
    analysis_chain.execute.return_value = MagicMock(data=[_FAKE_ANALYSIS_ROW])

    upsert_chain = _chain("upsert")
    upsert_chain.execute.return_value = MagicMock(data=[])

    call_count = {"n": 0}
    def table_side_effect(name):
        call_count["n"] += 1
        if name == "recommendation_cache" and call_count["n"] == 1:
            return cache_chain
        if name == "style_analyses":
            return analysis_chain
        return upsert_chain  # cache write

    mock_supabase.table.side_effect = table_side_effect

    # Claude call 1: generate_search_queries
    queries_resp = MagicMock()
    queries_resp.content = [MagicMock(text='{"queries":["navy slim chinos","minimalist white tee"]}')]

    # Claude call 2: annotate_recommendations
    annotate_resp = MagicMock()
    annotate_resp.content = [MagicMock(text=json.dumps(_FAKE_PRODUCTS))]

    mock_anthropic.messages.create.side_effect = [queries_resp, annotate_resp]

    # RapidAPI /search-v2 response
    rapidapi_resp = MagicMock()
    rapidapi_resp.raise_for_status.return_value = None
    rapidapi_resp.json.return_value = {
        "data": {"products": [{
            "product_id": "p1",
            "product_title": "Navy Slim Chinos",
            "product_photos": ["https://example.com/p1.jpg"],
            "product_page_url": "https://example.com/p1",
            "offer": {"store_name": "Gap", "price": "$55", "offer_page_url": "https://example.com/p1"},
        }]}
    }

    # Patch get_user_profile so generate_search_queries receives None instead
    # of a MagicMock that would make json.dumps fail inside the helper.
    with patch.object(flask_app, "get_user_profile", return_value=None), \
         patch.object(flask_app.req_lib, "get", return_value=rapidapi_resp):
        resp = c.post(
            f"/api/recommendations/{ANALYSIS_ID}",
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["cached"] is False
    assert len(body["recommendations"]) > 0
    assert mock_anthropic.messages.create.call_count == 2


def test_recommendations_not_found(client):
    """Returns 404 when the analysis row doesn't exist (or belongs to another user)."""
    c, mock_supabase, _ = client
    _mock_user(mock_supabase)

    cache_chain = _chain("select", "eq", "limit")
    cache_chain.execute.return_value = MagicMock(data=[])  # cache miss

    analysis_chain = _chain("select", "eq", "limit")
    analysis_chain.execute.return_value = MagicMock(data=[])  # not found

    call_count = {"n": 0}
    def table_side_effect(name):
        call_count["n"] += 1
        if name == "recommendation_cache":
            return cache_chain
        return analysis_chain

    mock_supabase.table.side_effect = table_side_effect

    resp = c.post(
        "/api/recommendations/nonexistent-id",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_recommendations_delete_requires_auth(client):
    """DELETE /api/recommendations/<id> with no token must return 401."""
    c, *_ = client
    resp = c.delete(f"/api/recommendations/{ANALYSIS_ID}")
    assert resp.status_code == 401


def test_recommendations_delete_clears_cache(client):
    """DELETE /api/recommendations/<id> clears the cache row and returns {deleted: true}."""
    c, mock_supabase, _ = client
    _mock_user(mock_supabase)

    del_chain = _chain("delete", "eq")
    del_chain.execute.return_value = MagicMock(data=[{"analysis_id": ANALYSIS_ID}])
    mock_supabase.table.return_value = del_chain

    resp = c.delete(
        f"/api/recommendations/{ANALYSIS_ID}",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": True}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

def test_signup_rejects_short_password(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "ab1cd23"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_signup_rejects_password_without_number(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "abcdefgh"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_signup_rejects_password_without_letter(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "12345678"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_signup_accepts_valid_password(client):
    c, mock_supabase, _ = client
    mock_user = MagicMock()
    mock_user.model_dump.return_value = {"id": "user-xyz", "email": "user@example.com"}
    mock_session = MagicMock()
    mock_session.model_dump.return_value = {"access_token": "tok", "token_type": "bearer"}
    mock_supabase.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)

    resp = c.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "abcd1234"},
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

def test_signup_rejects_invalid_email(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_login_rejects_invalid_email(client):
    c, *_ = client
    resp = c.post(
        "/api/auth/login",
        json={"email": "bad@@email", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# File size limit on upload
# ---------------------------------------------------------------------------

def test_upload_rejects_oversized_file(client):
    c, mock_supabase, _ = client
    import io

    # Mock get_user for token validation
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Create a fake file just over the 10 MB limit
    oversized_bytes = b"x" * (10 * 1024 * 1024 + 1)
    data = {"file": (io.BytesIO(oversized_bytes), "big.jpg", "image/jpeg")}
    resp = c.post(
        "/api/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 413
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_security_headers_present(client):
    c, *_ = client
    resp = c.get("/api/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------

def test_history_requires_auth(client):
    """GET /api/history with no token must return 401."""
    c, *_ = client
    resp = c.get("/api/history")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_history_with_valid_token(client):
    """GET /api/history with a valid token returns 200 and the correct shape."""
    c, mock_supabase, _ = client

    # Mock token → user resolution
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Mock the Supabase table query returning two rows
    fake_rows = [
        {
            "id": "aa000000-0000-0000-0000-000000000001",
            "user_id": "user-123",
            "image_url": "https://fake.supabase.co/img1.jpg",
            "colors": ["navy"],
            "silhouettes": ["slim-fit"],
            "style_tags": ["casual"],
            "summary": "A navy look.",
            "created_at": "2024-01-02T10:00:00Z",
        },
        {
            "id": "aa000000-0000-0000-0000-000000000002",
            "user_id": "user-123",
            "image_url": "https://fake.supabase.co/img2.jpg",
            "colors": ["white"],
            "silhouettes": ["oversized"],
            "style_tags": ["streetwear"],
            "summary": "A white streetwear look.",
            "created_at": "2024-01-01T10:00:00Z",
        },
    ]
    mock_query = MagicMock()
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=fake_rows)
    mock_supabase.table.return_value = mock_query

    resp = c.get(
        "/api/history",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "analyses" in body
    assert isinstance(body["analyses"], list)
    assert len(body["analyses"]) == 2
    # Verify shape of the first row
    first = body["analyses"][0]
    assert "id" in first
    assert "image_url" in first
    assert "colors" in first
    assert "summary" in first


def test_analyze_calls_save_analysis(client):
    """A successful /api/analyze call triggers save_analysis (table insert)."""
    c, mock_supabase, mock_anthropic = client
    import sys
    from unittest.mock import patch as _patch

    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    # Claude returns valid structured JSON
    claude_response = MagicMock()
    claude_response.content = [MagicMock()]
    claude_response.content[0].text = json.dumps({
        "colors": ["black"],
        "silhouettes": ["tailored"],
        "style_tags": ["formal"],
        "summary": "A sharp formal outfit.",
    })
    mock_anthropic.messages.create.return_value = claude_response

    # Token → user resolution
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Track table().insert().execute() calls; return a real UUID so
    # analysis_id is JSON-serialisable when included in the response.
    mock_insert_chain = MagicMock()
    mock_insert_chain.insert.return_value = mock_insert_chain
    mock_insert_chain.execute.return_value = MagicMock(
        data=[{"id": "00000000-0000-0000-0000-000000000001"}]
    )
    mock_supabase.table.return_value = mock_insert_chain

    mock_img_response = MagicMock()
    mock_img_response.content = b"fake-image-bytes"
    mock_img_response.headers = {"Content-Type": "image/jpeg"}
    mock_img_response.raise_for_status.return_value = None

    with _patch.object(flask_app, "get_user_profile", return_value=None), \
         _patch.object(flask_app.req_lib, "get", return_value=mock_img_response):
        resp = c.post(
            "/api/analyze",
            json={"image_url": "https://fake.supabase.co/storage/v1/object/public/img.jpg"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    # Verify that supabase.table("style_analyses") was called (insert happened)
    table_calls = [call.args[0] for call in mock_supabase.table.call_args_list]
    assert "style_analyses" in table_calls


# ---------------------------------------------------------------------------
# DELETE /api/history/<id>
# ---------------------------------------------------------------------------

def test_delete_history_requires_auth(client):
    """DELETE /api/history/<id> with no token must return 401."""
    c, *_ = client
    resp = c.delete("/api/history/some-uuid")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_delete_history_success(client):
    """DELETE /api/history/<id> with a valid token returns 200 + {deleted: true}."""
    c, mock_supabase, _ = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Supabase delete chain returns one deleted row
    mock_query = MagicMock()
    mock_query.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "aa000000-0000-0000-0000-000000000001"}])
    mock_supabase.table.return_value = mock_query

    resp = c.delete(
        "/api/history/aa000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": True}


def test_delete_history_not_found(client):
    """DELETE /api/history/<id> returns 404 when no row matched."""
    c, mock_supabase, _ = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Supabase delete returns empty data (no row matched / not owner)
    mock_query = MagicMock()
    mock_query.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = mock_query

    resp = c.delete(
        "/api/history/nonexistent-uuid",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# Analyze — oversized remote image
# ---------------------------------------------------------------------------

def test_analyze_rejects_oversized_remote_image(client):
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]

    # Mock a remote image response that reports a large Content-Length
    mock_img_response = MagicMock()
    mock_img_response.headers = {"Content-Length": str(10 * 1024 * 1024 + 1), "Content-Type": "image/jpeg"}
    mock_img_response.raise_for_status.return_value = None

    with patch.object(flask_app.req_lib, "get", return_value=mock_img_response):
        resp = c.post(
            "/api/analyze",
            json={"image_url": "https://fake.supabase.co/storage/v1/object/public/img.jpg"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 413
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# User profile endpoints
# ---------------------------------------------------------------------------

def test_profile_requires_auth(client):
    """Both GET and PUT /api/profile return 401 without a token."""
    c, *_ = client
    assert c.get("/api/profile").status_code == 401
    assert c.put("/api/profile", json={}).status_code == 401


def test_get_profile_returns_null_when_missing(client):
    """GET /api/profile returns {profile: null} when no row exists."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    q = MagicMock()
    q.select.return_value = q
    q.eq.return_value = q
    q.limit.return_value = q
    q.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = q

    resp = c.get("/api/profile", headers={"Authorization": f"Bearer {FAKE_JWT}"})
    assert resp.status_code == 200
    assert resp.get_json() == {"profile": None}


def test_update_profile_creates_new_row(client):
    """PUT /api/profile creates a profile and returns it."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    saved_row = {"user_id": "user-123", "gender": "male", "age_range": "25-34"}
    upsert_chain = MagicMock()
    upsert_chain.upsert.return_value = upsert_chain
    upsert_chain.execute.return_value = MagicMock(data=[saved_row])
    mock_supabase.table.return_value = upsert_chain

    resp = c.put(
        "/api/profile",
        json={"gender": "male", "age_range": "25-34"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["profile"]["gender"] == "male"
    assert body["profile"]["age_range"] == "25-34"


def test_update_profile_updates_existing_row(client):
    """PUT /api/profile upserts and returns the updated row."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    updated_row = {"user_id": "user-123", "preferred_styles": ["minimalist", "streetwear"]}
    upsert_chain = MagicMock()
    upsert_chain.upsert.return_value = upsert_chain
    upsert_chain.execute.return_value = MagicMock(data=[updated_row])
    mock_supabase.table.return_value = upsert_chain

    resp = c.put(
        "/api/profile",
        json={"preferred_styles": ["minimalist", "streetwear"]},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["profile"]["preferred_styles"] == ["minimalist", "streetwear"]


def test_update_profile_ignores_unknown_fields(client):
    """PUT /api/profile silently drops fields not in the allowlist."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    saved_row = {"user_id": "user-123", "gender": "female"}
    upsert_chain = MagicMock()
    upsert_chain.upsert.return_value = upsert_chain
    upsert_chain.execute.return_value = MagicMock(data=[saved_row])
    mock_supabase.table.return_value = upsert_chain

    resp = c.put(
        "/api/profile",
        json={"gender": "female", "evil_field": "DROP TABLE users;"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    call_args = upsert_chain.upsert.call_args
    payload_sent = call_args[0][0]
    assert "evil_field" not in payload_sent


def test_update_profile_validates_types(client):
    """PUT /api/profile returns 400 when an integer field receives a string."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    resp = c.put(
        "/api/profile",
        json={"height_cm": "tall"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# Wardrobe endpoints
# ---------------------------------------------------------------------------

_FAKE_WARDROBE_ITEM = {
    "id": "ww000000-0000-0000-0000-000000000001",
    "user_id": "user-123",
    "image_url": (
        "https://fake.supabase.co/storage/v1/object/public/wardrobe-items"
        "/user-123/ww000000.jpg"
    ),
    "ownership": "owned",
    "category": "top",
    "colors": ["navy", "white"],
    "style_tags": ["casual", "minimalist"],
    "description": "A navy and white striped t-shirt.",
    "user_notes": "",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
}

_FAKE_TAG_RESPONSE = json.dumps({
    "category": "top",
    "colors": ["navy", "white"],
    "style_tags": ["casual", "minimalist"],
    "description": "A navy and white striped t-shirt.",
})


def test_wardrobe_upload_requires_auth(client):
    """POST /api/wardrobe/upload with no token must return 401."""
    c, *_ = client
    resp = c.post("/api/wardrobe/upload")
    assert resp.status_code == 401


def test_wardrobe_upload_success(client):
    """Upload one valid image: Claude tags it, row is inserted, 201 returned."""
    import io
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.get_public_url.return_value = (
        _FAKE_WARDROBE_ITEM["image_url"]
    )

    # Claude tagging response
    tag_resp = MagicMock()
    tag_resp.content = [MagicMock(text=_FAKE_TAG_RESPONSE)]
    mock_anthropic.messages.create.return_value = tag_resp

    # DB insert returns the new row
    insert_chain = MagicMock()
    insert_chain.insert.return_value = insert_chain
    insert_chain.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = insert_chain

    data = {
        "files": (io.BytesIO(b"fake-image-bytes"), "shirt.jpg", "image/jpeg"),
        "ownership": "owned",
    }
    resp = c.post(
        "/api/wardrobe/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert len(body["items"]) == 1
    assert body["items"][0]["category"] == "top"
    assert body["failures"] == []


def test_wardrobe_upload_partial_failure(client):
    """Two files: Claude fails for the second; partial success returns 201."""
    import io
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp
    mock_supabase.storage.from_.return_value.upload.return_value = None
    mock_supabase.storage.from_.return_value.get_public_url.return_value = (
        _FAKE_WARDROBE_ITEM["image_url"]
    )

    # First Claude call succeeds; second raises
    tag_resp = MagicMock()
    tag_resp.content = [MagicMock(text=_FAKE_TAG_RESPONSE)]
    mock_anthropic.messages.create.side_effect = [
        tag_resp,
        Exception("Claude quota exceeded"),
    ]

    insert_chain = MagicMock()
    insert_chain.insert.return_value = insert_chain
    insert_chain.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = insert_chain

    data = {
        "files": [
            (io.BytesIO(b"img1"), "a.jpg", "image/jpeg"),
            (io.BytesIO(b"img2"), "b.jpg", "image/jpeg"),
        ],
        "ownership": "owned",
    }
    resp = c.post(
        "/api/wardrobe/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert len(body["items"]) == 1
    assert len(body["failures"]) == 1
    assert "Claude quota exceeded" in body["failures"][0]["error"]


def test_wardrobe_list(client):
    """GET /api/wardrobe returns correct shape with all items."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    q = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = q

    resp = c.get("/api/wardrobe", headers={"Authorization": f"Bearer {FAKE_JWT}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "items" in body
    assert len(body["items"]) == 1
    assert body["items"][0]["category"] == "top"


def test_wardrobe_list_filter_ownership(client):
    """GET /api/wardrobe?ownership=owned applies an ownership filter."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    q = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = q

    resp = c.get(
        "/api/wardrobe?ownership=owned",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    # Verify eq was called with the ownership filter at some point
    eq_calls = [call.args for call in q.eq.call_args_list]
    assert ("ownership", "owned") in eq_calls


def test_wardrobe_patch_updates_item(client):
    """PATCH /api/wardrobe/<id> returns the updated row."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    updated_item = {**_FAKE_WARDROBE_ITEM, "user_notes": "Love this shirt"}
    q = MagicMock()
    for method in ("update", "eq"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=[updated_item])
    mock_supabase.table.return_value = q

    resp = c.patch(
        f"/api/wardrobe/{_FAKE_WARDROBE_ITEM['id']}",
        json={"user_notes": "Love this shirt"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["item"]["user_notes"] == "Love this shirt"


def test_wardrobe_delete_removes_item(client):
    """DELETE /api/wardrobe/<id> deletes the row and attempts storage removal."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    q = MagicMock()
    for method in ("delete", "eq"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = q
    mock_supabase.storage.from_.return_value.remove.return_value = None

    resp = c.delete(
        f"/api/wardrobe/{_FAKE_WARDROBE_ITEM['id']}",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": True}
    assert mock_supabase.storage.from_.return_value.remove.called


def test_derive_style_requires_minimum_items(client):
    """POST /api/wardrobe/derive-style returns 400 when fewer than 5 items exist."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    q = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM, _FAKE_WARDROBE_ITEM])
    mock_supabase.table.return_value = q

    resp = c.post(
        "/api/wardrobe/derive-style",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "5 items" in resp.get_json()["error"]


def test_derive_style_success(client):
    """POST /api/wardrobe/derive-style returns Claude-generated style suggestions."""
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    five_items = [_FAKE_WARDROBE_ITEM] * 6
    q = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(q, method).return_value = q
    q.execute.return_value = MagicMock(data=five_items)
    mock_supabase.table.return_value = q

    derive_resp = MagicMock()
    derive_resp.content = [MagicMock(text=json.dumps({
        "preferred_styles": ["minimalist", "casual"],
        "color_palette": ["navy", "white", "grey"],
        "style_summary": "Clean, understated wardrobe with a navy-white palette.",
    }))]
    mock_anthropic.messages.create.return_value = derive_resp

    resp = c.post(
        "/api/wardrobe/derive-style",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "preferred_styles" in body
    assert "color_palette" in body
    assert "style_summary" in body
    assert "minimalist" in body["preferred_styles"]


def test_apply_derived_merges_not_replaces(client):
    """POST /api/profile/apply-derived unions arrays and guards string fields."""
    c, mock_supabase, _ = client
    import sys
    flask_app = sys.modules["app"]

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    existing_profile = {
        "user_id": "user-123",
        "preferred_styles": ["casual"],
        "gender": "male",
    }
    upsert_chain = MagicMock()
    upsert_chain.upsert.return_value = upsert_chain
    upsert_chain.execute.return_value = MagicMock(data=[{
        "user_id": "user-123",
        "preferred_styles": ["casual", "minimalist"],
        "gender": "male",
    }])
    mock_supabase.table.return_value = upsert_chain

    with patch.object(flask_app, "get_user_profile", return_value=existing_profile):
        resp = c.post(
            "/api/profile/apply-derived",
            json={"preferred_styles": ["minimalist", "casual"]},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    # Verify upsert payload unions without duplicates
    payload_sent = upsert_chain.upsert.call_args[0][0]
    assert set(payload_sent["preferred_styles"]) == {"casual", "minimalist"}
    # "casual" was already in existing; should appear once only
    assert payload_sent["preferred_styles"].count("casual") == 1


def test_build_outfit_success(client):
    """POST /api/wardrobe/build-outfit builds outfit around anchor item with product enrichment."""
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # First table call: fetch anchor item; second: fetch rest of wardrobe
    anchor_chain = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(anchor_chain, method).return_value = anchor_chain
    anchor_chain.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])

    rest_chain = MagicMock()
    for method in ("select", "eq", "neq", "order", "limit"):
        getattr(rest_chain, method).return_value = rest_chain
    rest_chain.execute.return_value = MagicMock(data=[])

    wardrobe_queue = [anchor_chain, rest_chain]

    def table_side_effect(name):
        if name == "wardrobe_items" and wardrobe_queue:
            return wardrobe_queue.pop(0)
        return MagicMock()  # user_profiles or extra calls

    mock_supabase.table.side_effect = table_side_effect

    outfit_resp = MagicMock()
    outfit_resp.content = [MagicMock(text=json.dumps({
        "anchor_item_id": _FAKE_WARDROBE_ITEM["id"],
        "summary": "A cohesive casual look anchored by the striped t-shirt.",
        "wardrobe_pieces": [],
        "missing_pieces": [
            {"role": "bottom", "description": "slim navy chinos would complete this look"}
        ],
    }))]

    _FAKE_PRODUCTS = [
        {
            "product_id": "p1",
            "title": "Navy Chinos",
            "price": "49.99",
            "image_url": "https://example.com/p1.jpg",
            "product_url": "https://example.com/p1",
            "retailer": "StyleStore",
            "source_query": "slim navy chinos would complete this look",
        }
    ]
    _FAKE_ANNOTATED = [{**_FAKE_PRODUCTS[0], "why_it_matches": "Complements the navy stripes perfectly."}]

    annotate_resp = MagicMock()
    annotate_resp.content = [MagicMock(text=json.dumps(_FAKE_ANNOTATED))]

    # outfit build call first, then annotation call
    mock_anthropic.messages.create.side_effect = [outfit_resp, annotate_resp]

    with patch("app.search_products", return_value=_FAKE_PRODUCTS):
        resp = c.post(
            "/api/wardrobe/build-outfit",
            json={"anchor_item_id": _FAKE_WARDROBE_ITEM["id"], "occasion": "work"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "anchor_item_id" in body
    assert "summary" in body
    assert "wardrobe_pieces" in body
    assert "missing_pieces" in body
    piece = body["missing_pieces"][0]
    assert "products" in piece
    assert len(piece["products"]) == 1
    assert piece["products"][0]["title"] == "Navy Chinos"
    assert "why_it_matches" in piece["products"][0]


def test_build_outfit_product_search_failure(client):
    """POST /api/wardrobe/build-outfit returns 200 with empty products on search failure."""
    c, mock_supabase, mock_anthropic = client
    import sys
    flask_app = sys.modules["app"]
    setattr(flask_app, "anthropic_client", mock_anthropic)

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    anchor_chain = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(anchor_chain, method).return_value = anchor_chain
    anchor_chain.execute.return_value = MagicMock(data=[_FAKE_WARDROBE_ITEM])

    rest_chain = MagicMock()
    for method in ("select", "eq", "neq", "order", "limit"):
        getattr(rest_chain, method).return_value = rest_chain
    rest_chain.execute.return_value = MagicMock(data=[])

    wardrobe_queue = [anchor_chain, rest_chain]

    def table_side_effect(name):
        if name == "wardrobe_items" and wardrobe_queue:
            return wardrobe_queue.pop(0)
        return MagicMock()

    mock_supabase.table.side_effect = table_side_effect

    outfit_resp = MagicMock()
    outfit_resp.content = [MagicMock(text=json.dumps({
        "anchor_item_id": _FAKE_WARDROBE_ITEM["id"],
        "summary": "A casual look.",
        "wardrobe_pieces": [],
        "missing_pieces": [
            {"role": "shoes", "description": "white sneakers"}
        ],
    }))]
    mock_anthropic.messages.create.return_value = outfit_resp

    with patch("app.search_products", side_effect=Exception("RapidAPI unavailable")):
        resp = c.post(
            "/api/wardrobe/build-outfit",
            json={"anchor_item_id": _FAKE_WARDROBE_ITEM["id"]},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["missing_pieces"][0]["products"] == []


def test_build_outfit_anchor_not_found(client):
    """POST /api/wardrobe/build-outfit returns 404 when anchor UUID doesn't exist."""
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    anchor_chain = MagicMock()
    for method in ("select", "eq", "limit"):
        getattr(anchor_chain, method).return_value = anchor_chain
    anchor_chain.execute.return_value = MagicMock(data=[])  # not found
    mock_supabase.table.return_value = anchor_chain

    resp = c.post(
        "/api/wardrobe/build-outfit",
        json={"anchor_item_id": "00000000-0000-0000-0000-000000000999"},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Compare endpoint
# ---------------------------------------------------------------------------

_FAKE_ANALYSIS = {
    "id": "aaaaaaaa-0000-0000-0000-000000000001",
    "image_url": "https://fake.supabase.co/storage/v1/object/public/outfit-photos/u1/img.jpg",
    "colors": ["black", "white"],
    "silhouettes": ["slim"],
    "style_tags": ["streetwear"],
    "summary": "A clean streetwear look.",
}

_FAKE_COMPARISON = {
    "verdict": "A",
    "verdict_reason": "Outfit A is more versatile.",
    "outfit_a": {"strengths": ["clean lines"], "concerns": [], "best_for": "everyday"},
    "outfit_b": {"strengths": ["bold colour"], "concerns": ["too loud"], "best_for": "weekend"},
    "contextual_notes": "Both outfits are solid choices.",
}



def _mock_claude_compare(mock_anthropic):
    """Make anthropic_client.messages.create return a valid comparison JSON."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(_FAKE_COMPARISON))]
    mock_anthropic.messages.create.return_value = mock_msg


def test_compare_requires_auth(client):
    c, *_ = client
    resp = c.post(
        "/api/compare",
        json={
            "outfit_a": {"analysis_id": "aaa"},
            "outfit_b": {"analysis_id": "bbb"},
        },
    )
    assert resp.status_code == 401


def test_compare_invalid_input_missing_outfit(client):
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    resp = c.post(
        "/api/compare",
        json={"outfit_a": {"analysis_id": "aaa"}},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "outfit_b" in resp.get_json()["error"]


def test_compare_invalid_input_no_source(client):
    c, mock_supabase, _ = client
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    resp = c.post(
        "/api/compare",
        json={"outfit_a": {}, "outfit_b": {"analysis_id": "bbb"}},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "analysis_id" in resp.get_json()["error"] or "image_url" in resp.get_json()["error"]


def test_compare_with_two_analysis_ids(client):
    c, mock_supabase, mock_anthropic = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # Two sequential style_analyses lookups + one profile lookup (returns nothing)
    call_count = [0]

    def _table_side_effect(name):
        chain = MagicMock()
        for m in ("select", "eq", "limit"):
            getattr(chain, m).return_value = chain

        if name == "style_analyses":
            call_count[0] += 1
            if call_count[0] == 1:
                chain.execute.return_value = MagicMock(data=[_FAKE_ANALYSIS])
            else:
                second = dict(_FAKE_ANALYSIS)
                second["id"] = "aaaaaaaa-0000-0000-0000-000000000002"
                chain.execute.return_value = MagicMock(data=[second])
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_supabase.table.side_effect = _table_side_effect
    _mock_claude_compare(mock_anthropic)

    resp = c.post(
        "/api/compare",
        json={
            "outfit_a": {"analysis_id": "aaaaaaaa-0000-0000-0000-000000000001"},
            "outfit_b": {"analysis_id": "aaaaaaaa-0000-0000-0000-000000000002"},
            "occasion": "Work",
        },
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "comparison" in body
    assert "outfit_a" in body
    assert "outfit_b" in body
    assert body["comparison"]["verdict"] == "A"


def test_compare_with_analysis_id_not_found(client):
    c, mock_supabase, _ = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    chain = MagicMock()
    for m in ("select", "eq", "limit"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[])  # not found
    mock_supabase.table.return_value = chain

    resp = c.post(
        "/api/compare",
        json={
            "outfit_a": {"analysis_id": "nonexistent-id"},
            "outfit_b": {"analysis_id": "another-nonexistent"},
        },
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "not found" in resp.get_json()["error"]


def test_compare_with_one_analysis_id_and_one_image_url(client):
    c, mock_supabase, mock_anthropic = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    # style_analyses fetch for outfit_a returns a row; insert for save_analysis
    call_count = [0]

    def _table_side_effect(name):
        chain = MagicMock()
        for m in ("select", "eq", "limit"):
            getattr(chain, m).return_value = chain
        chain.insert.return_value = chain
        if name == "style_analyses":
            call_count[0] += 1
            if call_count[0] == 1:
                chain.execute.return_value = MagicMock(data=[_FAKE_ANALYSIS])
            else:
                chain.execute.return_value = MagicMock(data=[{"id": "new-saved-id"}])
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_supabase.table.side_effect = _table_side_effect

    # Two Claude calls: vision analysis + comparison
    vision_json = {
        "colors": ["navy"],
        "silhouettes": ["relaxed"],
        "style_tags": ["casual"],
        "summary": "A relaxed casual outfit.",
    }
    call_index = [0]

    def _claude_side_effect(**_):
        call_index[0] += 1
        mock_msg = MagicMock()
        if call_index[0] == 1:
            mock_msg.content = [MagicMock(text=json.dumps(vision_json))]
        else:
            mock_msg.content = [MagicMock(text=json.dumps(_FAKE_COMPARISON))]
        return mock_msg

    mock_anthropic.messages.create.side_effect = _claude_side_effect

    image_url = f"https://fake.supabase.co/storage/v1/object/public/outfit-photos/u1/b.jpg"

    with patch("app.req_lib.get") as mock_get:
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "image/jpeg", "Content-Length": "1000"}
        mock_response.content = b"\xff\xd8\xff" + b"\x00" * 100
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        resp = c.post(
            "/api/compare",
            json={
                "outfit_a": {"analysis_id": "aaaaaaaa-0000-0000-0000-000000000001"},
                "outfit_b": {"image_url": image_url},
            },
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["comparison"]["verdict"] == "A"
    assert body["outfit_b"]["image_url"] == image_url


def test_compare_with_two_new_images(client):
    c, mock_supabase, mock_anthropic = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    chain = MagicMock()
    for m in ("select", "eq", "limit"):
        getattr(chain, m).return_value = chain
    chain.insert.return_value = chain
    chain.execute.return_value = MagicMock(data=[{"id": "saved-id"}])
    mock_supabase.table.return_value = chain

    vision_json = {
        "colors": ["red"],
        "silhouettes": ["oversized"],
        "style_tags": ["bold"],
        "summary": "A bold look.",
    }
    call_index = [0]

    def _claude_side_effect(**_):
        call_index[0] += 1
        mock_msg = MagicMock()
        if call_index[0] <= 2:
            mock_msg.content = [MagicMock(text=json.dumps(vision_json))]
        else:
            mock_msg.content = [MagicMock(text=json.dumps(_FAKE_COMPARISON))]
        return mock_msg

    mock_anthropic.messages.create.side_effect = _claude_side_effect

    url_a = "https://fake.supabase.co/storage/v1/object/public/outfit-photos/u1/a.jpg"
    url_b = "https://fake.supabase.co/storage/v1/object/public/outfit-photos/u1/b.jpg"

    with patch("app.req_lib.get") as mock_get:
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "image/jpeg", "Content-Length": "500"}
        mock_response.content = b"\xff\xd8\xff" + b"\x00" * 50
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        resp = c.post(
            "/api/compare",
            json={
                "outfit_a": {"image_url": url_a},
                "outfit_b": {"image_url": url_b},
            },
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "comparison" in body
    assert body["outfit_a"]["image_url"] == url_a
    assert body["outfit_b"]["image_url"] == url_b


# ---------------------------------------------------------------------------
# Generate a Look endpoint
# ---------------------------------------------------------------------------

_FAKE_LOOK_RESULT = {
    "title": "Relaxed Downtown",
    "summary": "A clean streetwear look built around neutral tones.",
    "wardrobe_pieces": [
        {"item_id": "item-001", "role": "top", "reason": "Pairs well with the vibe."},
    ],
    "missing_pieces": [
        {"role": "shoes", "description": "chunky white sneakers"},
    ],
}

_FAKE_WARDROBE_ITEM = {
    "id": "item-001",
    "category": "top",
    "colors": ["black"],
    "style_tags": ["streetwear"],
    "description": "Black oversized tee",
    "ownership": "owned",
    "image_url": "https://fake.supabase.co/storage/v1/object/public/wardrobe-items/u1/top.jpg",
}

_FAKE_PRODUCTS = [
    {
        "product_id": "p1",
        "title": "Chunky White Sneaker",
        "price": "89.99",
        "image_url": "https://img.example.com/sneaker.jpg",
        "product_url": "https://shop.example.com/sneaker",
        "retailer": "ShoeStore",
        "source_query": "chunky white sneakers",
    }
]


def _setup_generate_look_mocks(mock_supabase, wardrobe_data=None, profile_data=None):
    """Wire mock_supabase for the generate-look endpoint."""
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    wardrobe_data = wardrobe_data if wardrobe_data is not None else [_FAKE_WARDROBE_ITEM]
    profile_data = profile_data if profile_data is not None else [{"gender": "male", "budget_max_usd": 150}]

    call_count = [0]

    def _table_side_effect(name):
        chain = MagicMock()
        for m in ("select", "eq", "order", "limit", "insert"):
            getattr(chain, m).return_value = chain

        call_count[0] += 1
        if name == "wardrobe_items":
            chain.execute.return_value = MagicMock(data=wardrobe_data)
        else:
            chain.execute.return_value = MagicMock(data=profile_data)
        return chain

    mock_supabase.table.side_effect = _table_side_effect


def test_generate_look_requires_auth(client):
    c, *_ = client
    resp = c.post("/api/looks/generate", json={"occasion": "work"})
    assert resp.status_code == 401


def test_generate_look_success_with_all_inputs(client):
    c, mock_supabase, mock_anthropic = client
    _setup_generate_look_mocks(mock_supabase)

    # Claude returns the look JSON
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(_FAKE_LOOK_RESULT))]
    mock_anthropic.messages.create.return_value = mock_msg

    with patch("app.search_products", return_value=_FAKE_PRODUCTS), \
         patch("app.annotate_recommendations", return_value=_FAKE_PRODUCTS):
        resp = c.post(
            "/api/looks/generate",
            json={"occasion": "Work", "weather": "Cold", "vibe": "Minimalist", "notes": "Comfortable"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Relaxed Downtown"
    assert "wardrobe_pieces" in body
    assert "missing_pieces" in body
    assert "wardrobe_items" in body
    assert body["missing_pieces"][0]["products"] == _FAKE_PRODUCTS


def test_generate_look_success_no_inputs(client):
    c, mock_supabase, mock_anthropic = client
    _setup_generate_look_mocks(mock_supabase)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(_FAKE_LOOK_RESULT))]
    mock_anthropic.messages.create.return_value = mock_msg

    with patch("app.search_products", return_value=[]), \
         patch("app.annotate_recommendations", return_value=[]):
        resp = c.post(
            "/api/looks/generate",
            json={},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "title" in body
    assert "wardrobe_items" in body


def test_generate_look_product_search_failure(client):
    c, mock_supabase, mock_anthropic = client
    _setup_generate_look_mocks(mock_supabase)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(_FAKE_LOOK_RESULT))]
    mock_anthropic.messages.create.return_value = mock_msg

    def _search_raises(_):
        raise RuntimeError("RapidAPI down")

    with patch("app.search_products", side_effect=_search_raises):
        resp = c.post(
            "/api/looks/generate",
            json={"vibe": "Streetwear"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["missing_pieces"][0]["products"] == []


def test_generate_look_no_wardrobe(client):
    c, mock_supabase, mock_anthropic = client
    _setup_generate_look_mocks(mock_supabase, wardrobe_data=[])

    all_missing = {
        "title": "Street Ready",
        "summary": "A fresh look built entirely from scratch.",
        "wardrobe_pieces": [],
        "missing_pieces": [
            {"role": "top", "description": "white oversized tee"},
            {"role": "bottom", "description": "black slim joggers"},
        ],
    }
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(all_missing))]
    mock_anthropic.messages.create.return_value = mock_msg

    with patch("app.search_products", return_value=[]):
        resp = c.post(
            "/api/looks/generate",
            json={"occasion": "Casual weekend"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["wardrobe_pieces"] == []
    assert len(body["missing_pieces"]) == 2
    assert body["wardrobe_items"] == []


# ---------------------------------------------------------------------------
# Style Audit endpoints
# ---------------------------------------------------------------------------

_FAKE_AUDIT_RESULT = {
    "summary": "A solid casual wardrobe that lacks versatility for smarter occasions.",
    "strengths": ["Good variety of tops", "Strong streetwear palette"],
    "gaps": [
        {
            "id": "neutral-bottoms",
            "title": "Neutral Bottoms",
            "description": "No neutral trousers to pair with statement tops.",
            "suggested_search": "neutral slim trousers",
        },
        {
            "id": "outerwear",
            "title": "Outerwear",
            "description": "No coat or jacket for cooler days.",
            "suggested_search": "minimalist overcoat",
        },
        {
            "id": "smart-shoes",
            "title": "Smart Shoes",
            "description": "Only trainers — nothing for smarter occasions.",
            "suggested_search": "clean leather shoes",
        },
    ],
}

_FAKE_GAP_PRODUCTS = [
    {
        "product_id": "p1",
        "title": "Slim Neutral Chino",
        "price": "65.00",
        "image_url": "https://img.example.com/chino.jpg",
        "product_url": "https://shop.example.com/chino",
        "retailer": "ThreadCo",
        "source_query": "neutral slim trousers",
    },
    {
        "product_id": "p2",
        "title": "Dark Khaki Trousers",
        "price": "72.00",
        "image_url": "https://img.example.com/khaki.jpg",
        "product_url": "https://shop.example.com/khaki",
        "retailer": "StyleStore",
        "source_query": "neutral slim trousers",
    },
    {
        "product_id": "p3",
        "title": "Stone Linen Trousers",
        "price": "58.00",
        "image_url": "https://img.example.com/linen.jpg",
        "product_url": "https://shop.example.com/linen",
        "retailer": "ModernBasics",
        "source_query": "neutral slim trousers",
    },
]


def _make_wardrobe_items(count):
    return [
        {
            "category": "top",
            "colors": ["black"],
            "style_tags": ["streetwear"],
            "ownership": "owned",
        }
        for _ in range(count)
    ]


def _setup_audit_mocks(mock_supabase, wardrobe_count=8):
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    call_count = [0]

    def _table_side_effect(name):
        chain = MagicMock()
        for m in ("select", "eq", "order", "limit"):
            getattr(chain, m).return_value = chain

        call_count[0] += 1
        if name == "wardrobe_items":
            chain.execute.return_value = MagicMock(data=_make_wardrobe_items(wardrobe_count))
        else:
            chain.execute.return_value = MagicMock(data=[])
        return chain

    mock_supabase.table.side_effect = _table_side_effect


def test_audit_requires_auth(client):
    c, *_ = client
    resp = c.post("/api/wardrobe/audit")
    assert resp.status_code == 401


def test_audit_too_few_items(client):
    c, mock_supabase, _ = client
    _setup_audit_mocks(mock_supabase, wardrobe_count=3)

    resp = c.post(
        "/api/wardrobe/audit",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 400
    assert "5 items" in resp.get_json()["error"]


def test_audit_success(client):
    c, mock_supabase, mock_anthropic = client
    _setup_audit_mocks(mock_supabase, wardrobe_count=8)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(_FAKE_AUDIT_RESULT))]
    mock_anthropic.messages.create.return_value = mock_msg

    resp = c.post(
        "/api/wardrobe/audit",
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "summary" in body
    assert "strengths" in body
    assert "gaps" in body
    assert 3 <= len(body["gaps"]) <= 6
    gap = body["gaps"][0]
    assert "id" in gap
    assert "title" in gap
    assert "description" in gap
    assert "suggested_search" in gap


def test_fill_gap_requires_auth(client):
    c, *_ = client
    resp = c.post(
        "/api/wardrobe/audit/fill-gap",
        json={"gap_title": "Neutral Bottoms", "suggested_search": "neutral slim trousers"},
    )
    assert resp.status_code == 401


def test_fill_gap_success(client):
    c, mock_supabase, mock_anthropic = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    chain = MagicMock()
    for m in ("select", "eq", "limit"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = chain

    with patch("app.search_products", return_value=_FAKE_GAP_PRODUCTS), \
         patch("app.annotate_recommendations", return_value=_FAKE_GAP_PRODUCTS):
        resp = c.post(
            "/api/wardrobe/audit/fill-gap",
            json={
                "gap_title": "Neutral Bottoms",
                "gap_description": "No neutral trousers.",
                "suggested_search": "neutral slim trousers",
            },
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "products" in body
    assert len(body["products"]) == 3


def test_fill_gap_search_failure(client):
    c, mock_supabase, _ = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    chain = MagicMock()
    for m in ("select", "eq", "limit"):
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    mock_supabase.table.return_value = chain

    with patch("app.search_products", side_effect=RuntimeError("RapidAPI down")):
        resp = c.post(
            "/api/wardrobe/audit/fill-gap",
            json={"gap_title": "Outerwear", "suggested_search": "minimalist overcoat"},
            headers={"Authorization": f"Bearer {FAKE_JWT}"},
        )

    assert resp.status_code == 502
    assert "error" in resp.get_json()
