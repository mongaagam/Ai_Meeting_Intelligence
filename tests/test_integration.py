from fastapi.testclient import TestClient

from backend.main import app
from backend.api.dependencies import get_current_user


def test_api_root_and_protected_routes():
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.json()["message"] == "AI Meeting Intelligence API is running"

        meetings = client.get("/meetings/")
        assert meetings.status_code in (401, 403)


def test_authenticated_route_dependency_override():
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 987654,
        "email": "integration-test@example.com",
    }
    try:
        with TestClient(app) as client:
            response = client.get("/auth/users/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {"id": 987654, "email": "integration-test@example.com"}
