from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.dependencies import get_current_user
from backend.api import meetings as meetings_api


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def authenticated_client():
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 987654,
        "email": "meeting-test@example.com",
    }
    with TestClient(app) as test_client:

        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def test_meeting_list_requires_authentication(client):
    response = client.get("/meetings/")
    assert response.status_code in (401, 403)


def test_meeting_count_requires_authentication(client):
    response = client.get("/meetings/count")
    assert response.status_code in (401, 403)


def test_meeting_details_requires_authentication(client):
    response = client.get("/meetings/999999")
    assert response.status_code in (401, 403)


def test_meeting_details_not_found(authenticated_client, monkeypatch):
    class FakeCursor:
        def execute(self, *args, **kwargs):
            return self

        def fetchone(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(meetings_api, "get_db", lambda: FakeConnection())

    response = authenticated_client.get("/meetings/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_upload_rejects_unsupported_file_type(
    authenticated_client, monkeypatch, tmp_path
):
    monkeypatch.setattr(meetings_api, "UPLOAD_DIR", tmp_path)

    response = authenticated_client.post(
        "/meetings/upload",
        files={
            "file": (
                "notes.txt",
                b"not a supported media file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file format"
    assert list(Path(tmp_path).iterdir()) == []


def test_upload_rejects_empty_audio(
    authenticated_client, monkeypatch, tmp_path
):
    monkeypatch.setattr(meetings_api, "UPLOAD_DIR", tmp_path)

    response = authenticated_client.post(
        "/meetings/upload",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"
    assert list(Path(tmp_path).iterdir()) == []


def test_upload_rejects_file_larger_than_limit(
    authenticated_client, monkeypatch, tmp_path
):
    monkeypatch.setattr(meetings_api, "UPLOAD_DIR", tmp_path)

    oversized_content = b"x" * (200 * 1024 * 1024 + 1)

    response = authenticated_client.post(
        "/meetings/upload",
        files={
            "file": (
                "large.mp4",
                oversized_content,
                "video/mp4",
            )
        },
    )

    assert response.status_code == 413
    assert list(Path(tmp_path).iterdir()) == []


def test_upload_rejects_missing_file(authenticated_client):
    response = authenticated_client.post("/meetings/upload")
    assert response.status_code == 422


def test_meeting_list_only_returns_current_users_meetings(
    authenticated_client, monkeypatch
):
    class FakeCursor:
        def __init__(self):
            self.query = ""
            self.params = ()

        def execute(self, query, params=()):
            self.query = query
            self.params = params
            return self

        def fetchone(self):
            return (1,)

        def fetchall(self):
            return [
                {
                    "id": 1,
                    "filename": "my_meeting.mp4",
                    "file_path": "data/uploads/my_meeting.mp4",
                    "status": "uploaded",
                    "created_at": "2026-10-23",
                }
            ]

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(meetings_api, "get_db", lambda: FakeConnection())

    response = authenticated_client.get("/meetings/")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["meetings"]) == 1
    assert response.json()["meetings"][0]["filename"] == "my_meeting.mp4"


def test_meeting_count_returns_current_users_count(
    authenticated_client, monkeypatch
):
    class FakeCursor:
        def execute(self, query, params=()):
            self.query = query
            self.params = params
            return self

        def fetchone(self):
            return {"total": 3}

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(meetings_api, "get_db", lambda: FakeConnection())

    response = authenticated_client.get("/meetings/count")

    assert response.status_code == 200
    assert response.json()["total_meetings"] == 3


def test_user_cannot_access_another_users_meeting(
    authenticated_client, monkeypatch
):
    executed_queries = []

    class FakeCursor:
        def execute(self, query, params=()):
            executed_queries.append((query, params))
            return self

        def fetchone(self):
            return None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(meetings_api, "get_db", lambda: FakeConnection())

    response = authenticated_client.get("/meetings/123")

    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"

    query, params = executed_queries[0]

    assert "m.user_id = ?" in query
    assert params == (123, 987654)

