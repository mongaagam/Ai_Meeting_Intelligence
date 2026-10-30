import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.dependencies import get_current_user
from backend.api import auth as auth_api


@pytest.fixture
def client():
    return TestClient(app)


def test_signup_success(client, monkeypatch):
    monkeypatch.setattr(
        auth_api, "get_user_by_email", lambda email: None
    )
    monkeypatch.setattr(
        auth_api, "create_user", lambda full_name, email, password: 123
    )

    response = client.post("/auth/signup", json={
        "full_name": "Test User",
        "email": "api-test@example.com",
        "password": "StrongTestPassword123!",
    })

    assert response.status_code == 200
    assert response.json()["message"] == "Account created successfully"
    assert response.json()["user_id"] == 123


def test_signup_duplicate_email(client, monkeypatch):
    monkeypatch.setattr(
        auth_api,
        "get_user_by_email",
        lambda email: {"id": 1, "email": email},
    )

    response = client.post("/auth/signup", json={
        "full_name": "Test User",
        "email": "existing@example.com",
        "password": "StrongTestPassword123!",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_login_success(client, monkeypatch):
    user = {
        "id": 123,
        "full_name": "Test User",
        "email": "api-test@example.com",
        "password_hash": "fake-hash",
    }

    monkeypatch.setattr(
        auth_api, "get_user_by_email", lambda email: user
    )
    monkeypatch.setattr(
        auth_api,
        "verify_password",
        lambda password, password_hash: True,
    )
    monkeypatch.setattr(
        auth_api,
        "create_access_token",
        lambda user_id, email: "test-token",
    )

    response = client.post("/auth/login", json={
        "email": "api-test@example.com",
        "password": "StrongTestPassword123!",
    })

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-token"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["id"] == 123


def test_login_unknown_email(client, monkeypatch):
    monkeypatch.setattr(
        auth_api, "get_user_by_email", lambda email: None
    )

    response = client.post("/auth/login", json={
        "email": "missing@example.com",
        "password": "wrong-password",
    })

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_wrong_password(client, monkeypatch):
    user = {
        "id": 123,
        "full_name": "Test User",
        "email": "api-test@example.com",
        "password_hash": "fake-hash",
    }

    monkeypatch.setattr(
        auth_api, "get_user_by_email", lambda email: user
    )
    monkeypatch.setattr(
        auth_api,
        "verify_password",
        lambda password, password_hash: False,
    )

    response = client.post("/auth/login", json={
        "email": "api-test@example.com",
        "password": "wrong-password",
    })

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_current_user_requires_authentication(client):
    response = client.get("/auth/users/me")
    assert response.status_code in (401, 403)


def test_current_user_with_mocked_user(client):
    app.dependency_overrides[get_current_user] = (
        lambda: {"id": 123, "email": "api-test@example.com"}
    )

    try:
        response = client.get("/auth/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "id": 123,
        "email": "api-test@example.com",
    }


def test_logout_requires_authentication(client):
    response = client.post("/auth/logout")
    assert response.status_code in (401, 403)

# Additional JWT security tests
from datetime import datetime, timedelta, timezone
from jose import jwt
from backend.api import dependencies


def test_invalid_jwt_token_is_rejected(client, monkeypatch):
    monkeypatch.setattr(dependencies, "JWT_SECRET_KEY", "test-secret")

    response = client.get(
        "/auth/users/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


def test_expired_jwt_token_is_rejected(client, monkeypatch):
    secret = "test-secret"
    monkeypatch.setattr(dependencies, "JWT_SECRET_KEY", secret)
    monkeypatch.setattr(dependencies, "JWT_ALGORITHM", "HS256")

    token = jwt.encode(
        {
            "sub": "123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_jwt_missing_email_is_rejected(client, monkeypatch):
    secret = "test-secret"
    monkeypatch.setattr(dependencies, "JWT_SECRET_KEY", secret)
    monkeypatch.setattr(dependencies, "JWT_ALGORITHM", "HS256")

    token = jwt.encode(
        {
            "sub": "123",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token payload"


def test_jwt_invalid_user_id_is_rejected(client, monkeypatch):
    secret = "test-secret"
    monkeypatch.setattr(dependencies, "JWT_SECRET_KEY", secret)
    monkeypatch.setattr(dependencies, "JWT_ALGORITHM", "HS256")

    token = jwt.encode(
        {
            "sub": "not-a-number",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
