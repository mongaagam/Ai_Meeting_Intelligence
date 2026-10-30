
import sqlite3
import pytest

from backend.db.database import init_db


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_users.db"

    # Use a temporary database, not the real project database.
    monkeypatch.setattr(
        "backend.db.database.DB_PATH",
        db_file
    )

    init_db()

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    yield conn

    conn.close()


def test_required_tables_created(test_db):
    rows = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()

    tables = {row["name"] for row in rows}

    expected_tables = {
        "users",
        "meetings",
        "ai_analysis",
        "meeting_speakers",
        "speaker_segments",
        "tasks",
    }

    assert expected_tables.issubset(tables)


def test_meeting_saved_for_existing_user(test_db):
    cursor = test_db.execute(
        """
        INSERT INTO users (full_name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        ("Test User", "db-test@example.com", "test-hash"),
    )
    user_id = cursor.lastrowid

    test_db.execute(
        """
        INSERT INTO meetings (user_id, filename, file_path)
        VALUES (?, ?, ?)
        """,
        (user_id, "test.mp3", "data/uploads/test.mp3"),
    )
    test_db.commit()

    meeting = test_db.execute(
        "SELECT * FROM meetings WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    assert meeting is not None
    assert meeting["filename"] == "test.mp3"
    assert meeting["status"] == "uploaded"


def test_meeting_rejects_nonexistent_user(test_db):
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute(
            """
            INSERT INTO meetings (user_id, filename)
            VALUES (?, ?)
            """,
            (99999, "orphan.mp3"),
        )


def test_analysis_saved_for_meeting(test_db):
    cursor = test_db.execute(
        """
        INSERT INTO users (full_name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        ("Test User", "analysis-test@example.com", "test-hash"),
    )
    user_id = cursor.lastrowid

    cursor = test_db.execute(
        """
        INSERT INTO meetings (user_id, filename)
        VALUES (?, ?)
        """,
        (user_id, "analysis.mp3"),
    )
    meeting_id = cursor.lastrowid

    test_db.execute(
        """
        INSERT INTO ai_analysis (meeting_id, transcript, summary)
        VALUES (?, ?, ?)
        """,
        (meeting_id, "We discussed project testing.", "Testing plan discussed."),
    )
    test_db.commit()

    analysis = test_db.execute(
        "SELECT * FROM ai_analysis WHERE meeting_id = ?",
        (meeting_id,),
    ).fetchone()

    assert analysis is not None
    assert analysis["transcript"] == "We discussed project testing."
    assert analysis["summary"] == "Testing plan discussed."


def test_task_saved_with_default_status(test_db):
    cursor = test_db.execute(
        """
        INSERT INTO users (full_name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        ("Test User", "task-test@example.com", "test-hash"),
    )
    user_id = cursor.lastrowid

    cursor = test_db.execute(
        """
        INSERT INTO meetings (user_id, filename)
        VALUES (?, ?)
        """,
        (user_id, "tasks.mp3"),
    )
    meeting_id = cursor.lastrowid

    cursor = test_db.execute(
        """
        INSERT INTO tasks (meeting_id, task, assignee_name)
        VALUES (?, ?, ?)
        """,
        (meeting_id, "Prepare report", "Test User"),
    )
    task_id = cursor.lastrowid
    test_db.commit()

    task = test_db.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()

    assert task is not None
    assert task["task"] == "Prepare report"
    assert task["assignee_name"] == "Test User"
    assert task["status"] == "Pending"


def test_deleting_meeting_cascades_to_related_data(test_db):
    cursor = test_db.execute(
        """
        INSERT INTO users (full_name, email, password_hash)
        VALUES (?, ?, ?)
        """,
        ("Test User", "delete-test@example.com", "test-hash"),
    )
    user_id = cursor.lastrowid

    cursor = test_db.execute(
        """
        INSERT INTO meetings (user_id, filename)
        VALUES (?, ?)
        """,
        (user_id, "delete.mp3"),
    )
    meeting_id = cursor.lastrowid

    test_db.execute(
        """
        INSERT INTO ai_analysis (meeting_id, transcript)
        VALUES (?, ?)
        """,
        (meeting_id, "Temporary test transcript"),
    )

    test_db.execute(
        """
        INSERT INTO tasks (meeting_id, task)
        VALUES (?, ?)
        """,
        (meeting_id, "Temporary test task"),
    )

    test_db.commit()

    test_db.execute(
        "DELETE FROM meetings WHERE id = ?",
        (meeting_id,),
    )
    test_db.commit()

    analysis_count = test_db.execute(
        "SELECT COUNT(*) FROM ai_analysis WHERE meeting_id = ?",
        (meeting_id,),
    ).fetchone()[0]

    task_count = test_db.execute(
        "SELECT COUNT(*) FROM tasks WHERE meeting_id = ?",
        (meeting_id,),
    ).fetchone()[0]

    assert analysis_count == 0
    assert task_count == 0
