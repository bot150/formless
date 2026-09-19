import io
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import decode_access_token
from app.main import app

# Create in-memory SQLite database specifically for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# -------------------------------------------------------------
# 1. REGISTRATION TESTS
# -------------------------------------------------------------
def test_valid_registration(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_duplicate_email_registration(client):
    client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "anotherpassword"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_registration_short_password(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "shortpw@example.com", "password": "123"},
    )
    assert response.status_code == 422


def test_password_is_hashed_and_not_stored_plaintext():
    from app.core.security import hash_password, verify_password

    raw = "mySecretPassword!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong", hashed) is False


# -------------------------------------------------------------
# 2. LOGIN TESTS
# -------------------------------------------------------------
def test_valid_login(client):
    client.post(
        "/api/auth/register",
        json={"email": "loginuser@example.com", "password": "mypassword123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "loginuser@example.com", "password": "mypassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@example.com"


def test_invalid_password_login(client):
    client.post(
        "/api/auth/register",
        json={"email": "testuser@example.com", "password": "mypassword123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "testuser@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


def test_nonexistent_user_login(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nosuchuser@example.com", "password": "mypassword123"},
    )
    assert response.status_code == 401


# -------------------------------------------------------------
# 3. GET /api/auth/me & TOKEN TESTS
# -------------------------------------------------------------
def test_get_me_authenticated(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "me@example.com", "password": "mypassword123"},
    )
    token = reg.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["profile"] is None


def test_get_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


# -------------------------------------------------------------
# 4. GOOGLE OAUTH FLOW TESTS
# -------------------------------------------------------------
def test_google_login_unconfigured(client):
    # When credentials are unset, returns 503 rather than crashing
    with patch("app.core.config.settings.google_client_id", ""), patch(
        "app.core.config.settings.google_client_secret", ""
    ):
        response = client.get("/api/auth/google/login")
        assert response.status_code == 503
        legacy_resp = client.get("/auth/google/login")
        assert legacy_resp.status_code == 503


def test_google_login_redirects_to_google_with_parameters(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers.get("location", "")
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=" in location
    assert "redirect_uri=" in location
    assert "scope=" in location
    assert "openid" in location
    assert "email" in location
    assert "profile" in location


def test_google_callback_creates_new_user(client):
    mock_userinfo = {
        "sub": "google-uid-12345",
        "email": "googlenew@example.com",
        "name": "Google User",
    }
    with patch(
        "app.api.auth_routes.oauth.google.authorize_access_token",
        new_callable=AsyncMock,
    ) as mock_auth, patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ), patch(
        "app.core.config.settings.google_redirect_uri",
        "http://127.0.0.1:8000/api/auth/google/callback",
    ):
        mock_auth.return_value = {"userinfo": mock_userinfo}
        response = client.get(
            "/api/auth/google/callback?code=mock_code", follow_redirects=False
        )
        assert response.status_code == 303
        assert "/profile/setup?token=" in response.headers["location"]

        token = response.headers["location"].split("token=")[1]
        payload = decode_access_token(token)
        assert payload["email"] == "googlenew@example.com"

        # Verify this token can authenticate GET /api/auth/me
        me_resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "googlenew@example.com"


def test_google_callback_links_existing_user(client):
    # First create normal user with same email
    client.post(
        "/api/auth/register",
        json={"email": "existing@example.com", "password": "password123"},
    )

    mock_userinfo = {
        "sub": "google-uid-67890",
        "email": "existing@example.com",
        "name": "Existing User",
    }
    with patch(
        "app.api.auth_routes.oauth.google.authorize_access_token",
        new_callable=AsyncMock,
    ) as mock_auth, patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ), patch(
        "app.core.config.settings.google_redirect_uri",
        "http://127.0.0.1:8000/api/auth/google/callback",
    ):
        mock_auth.return_value = {"userinfo": mock_userinfo}
        response = client.get(
            "/api/auth/google/callback?code=mock_code", follow_redirects=False
        )
        assert response.status_code == 303
        token = response.headers["location"].split("token=")[1]
        payload = decode_access_token(token)
        assert payload["email"] == "existing@example.com"


def test_google_callback_missing_code(client):
    with patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ):
        response = client.get("/api/auth/google/callback")
        assert response.status_code == 400
        assert "authorization code missing" in response.json()["detail"].lower()


def test_google_callback_provider_error(client):
    with patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ):
        response = client.get(
            "/api/auth/google/callback?error=access_denied&error_description=User+denied"
        )
        assert response.status_code == 400
        assert "google oauth error" in response.json()["detail"].lower()


def test_google_callback_token_exchange_error(client):
    with patch(
        "app.api.auth_routes.oauth.google.authorize_access_token",
        side_effect=Exception("OAuth exchange error"),
    ), patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ):
        response = client.get("/api/auth/google/callback?code=invalid_code")
        assert response.status_code == 400
        assert "failed to authenticate" in response.json()["detail"].lower()


def test_google_callback_missing_email(client):
    mock_userinfo = {
        "sub": "google-uid-no-email",
        "name": "No Email User",
    }
    with patch(
        "app.api.auth_routes.oauth.google.authorize_access_token",
        new_callable=AsyncMock,
    ) as mock_auth, patch(
        "app.core.config.settings.google_client_id", "test-id"
    ), patch(
        "app.core.config.settings.google_client_secret", "test-secret"
    ):
        mock_auth.return_value = {"userinfo": mock_userinfo}
        response = client.get("/api/auth/google/callback?code=mock_code")
        assert response.status_code == 400
        assert "valid email address" in response.json()["detail"].lower()



# -------------------------------------------------------------
# 5. AADHAAR PROFILE SETUP & CONFIRMATION TESTS
# -------------------------------------------------------------
def test_aadhaar_upload_unauthenticated(client):
    file_data = io.BytesIO(b"dummy image data")
    response = client.post(
        "/api/profile/aadhaar",
        files={"file": ("aadhaar.jpg", file_data, "image/jpeg")},
    )
    assert response.status_code == 401


def test_aadhaar_upload_unsupported_file(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "aadhaaruser@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    file_data = io.BytesIO(b"executable data")
    response = client.post(
        "/api/profile/aadhaar",
        files={"file": ("virus.exe", file_data, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "allowed formats" in response.json()["detail"].lower()


def test_aadhaar_upload_mock_extraction_success(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "aadhaaruser2@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    file_data = io.BytesIO(b"dummy aadhaar image bytes")
    response = client.post(
        "/api/profile/aadhaar",
        files={"file": ("aadhaar_front.png", file_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "local_mock"
    assert data["success"] is True
    assert data["name"] == "Example User"
    assert data["extracted_fields"]["name"] == "Example User"
    assert data["date_of_birth"] == "04/07/2007"
    assert data["gender"] == "Female"
    assert data["address"] == "Vijayawada, Andhra Pradesh"
    assert "aadhaar_number" not in data


def test_aadhaar_upload_corrupt_file_failure(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "corruptuser@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    file_data = io.BytesIO(b"corrupt file data")
    response = client.post(
        "/api/profile/aadhaar",
        files={"file": ("corrupt_aadhaar.png", file_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "corrupt or unreadable" in response.json()["detail"].lower()


def test_aadhaar_upload_no_fields_failure(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "nofieldsuser@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    file_data = io.BytesIO(b"no_fields detected in image")
    response = client.post(
        "/api/profile/aadhaar",
        files={"file": ("blank_aadhaar.png", file_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    data = response.json()
    # 422 returns structured detail
    detail = data["detail"]
    assert detail["success"] is False
    assert "unable to extract aadhaar details" in detail["message"].lower()
    assert "name" in detail["missing_fields"]


def test_profile_confirmation_associates_with_user(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "confirmuser@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    confirm_payload = {
        "name": "Girisha Varshini J",
        "date_of_birth": "04/07/2007",
        "gender": "Female",
        "address": "Vijayawada, Andhra Pradesh",
    }
    response = client.post(
        "/api/profile/confirm",
        json=confirm_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    profile_data = response.json()
    assert profile_data["name"] == "Girisha Varshini J"
    assert profile_data["date_of_birth"] == "04/07/2007"
    assert profile_data["gender"] == "Female"
    assert profile_data["address"] == "Vijayawada, Andhra Pradesh"

    # Verify /api/auth/me now reflects this profile
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["profile"] is not None
    assert me_data["profile"]["name"] == "Girisha Varshini J"


# -------------------------------------------------------------
# 6. SECURITY TESTS
# -------------------------------------------------------------
def test_jwt_does_not_contain_aadhaar_or_password(client):
    reg = client.post(
        "/api/auth/register",
        json={"email": "securityuser@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]
    payload = decode_access_token(token)
    assert "password" not in payload
    assert "password_hash" not in payload
    assert "aadhaar" not in payload
    assert "aadhaar_number" not in payload
    assert "user_id" in payload
    assert "email" in payload
    assert payload["email"] == "securityuser@example.com"


# -------------------------------------------------------------
# 7. STATIC UI ENDPOINTS TESTS
# -------------------------------------------------------------
def test_static_auth_and_profile_pages(client):
    auth_resp = client.get("/auth")
    assert auth_resp.status_code == 200
    assert "FORMLESS" in auth_resp.text

    profile_resp = client.get("/profile/setup")
    assert profile_resp.status_code == 200
    assert "Complete Your Formless Profile" in profile_resp.text
