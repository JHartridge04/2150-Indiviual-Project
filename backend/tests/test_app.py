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
    c, *_ = client
    resp = c.post("/api/recommendations", json={"style_tags": ["casual"]})
    assert resp.status_code == 401


def test_recommendations_with_token(client):
    c, mock_supabase, _ = client

    # Mock get_user
    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    resp = c.post(
        "/api/recommendations",
        json={"style_tags": ["casual"]},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "recommendations" in body
    assert len(body["recommendations"]) > 0


def test_recommendations_default_when_no_tags(client):
    c, mock_supabase, _ = client

    mock_user_resp = MagicMock()
    mock_user_resp.user.id = "user-123"
    mock_supabase.auth.get_user.return_value = mock_user_resp

    resp = c.post(
        "/api/recommendations",
        json={"style_tags": []},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # Should fall back to default recommendations
    assert len(body["recommendations"]) > 0


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
    flask_app.anthropic_client = mock_anthropic

    # Mock the image fetch (since analyze fetches image bytes from URL)
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
    flask_app.anthropic_client = mock_anthropic
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
# Recommendations — item structure
# ---------------------------------------------------------------------------

def test_recommendations_item_structure(client):
    c, mock_supabase, _ = client

    resp = c.post(
        "/api/recommendations",
        json={"style_tags": ["formal"]},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    items = body["recommendations"]
    assert len(items) > 0
    # Each item must have name, image, price, and link
    for item in items:
        assert "name" in item
        assert "image" in item
        assert "price" in item
        assert "link" in item
        assert item["link"].startswith("https://")


def test_recommendations_multiple_tags_deduplicates(client):
    c, mock_supabase, _ = client

    resp = c.post(
        "/api/recommendations",
        json={"style_tags": ["casual", "casual"]},
        headers={"Authorization": f"Bearer {FAKE_JWT}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    names = [item["name"] for item in body["recommendations"]]
    # No duplicate names
    assert len(names) == len(set(names))
