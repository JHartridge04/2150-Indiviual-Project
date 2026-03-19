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
