"""Shared task logic (local SQLite) used by pages/dashboard.py and pages/task.py."""
import ast
import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("data/users.db")
COMPLETED_STATUSES = {"completed", "complete", "done"}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def ensure_tasks_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            assignee_name TEXT NOT NULL,
            deadline TEXT DEFAULT 'Not specified',
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(meeting_id, task, assignee_name, deadline),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
        )
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "is_deleted" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()


def parse_action_items(raw_items):
    if not raw_items:
        return []
    if isinstance(raw_items, (list, dict)):
        parsed = raw_items
    else:
        parsed = None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(raw_items)
                break
            except (ValueError, SyntaxError, TypeError):
                continue
    if isinstance(parsed, dict):
        parsed = [parsed]
    return parsed if isinstance(parsed, list) else []


def sync_ai_tasks(conn, user_id, user_name):
    """Import AI action items assigned to this user without overwriting statuses."""
    if not table_exists(conn, "meetings") or not table_exists(conn, "ai_analysis"):
        return

    meetings = conn.execute(
        """
        SELECT m.id AS meeting_id, m.filename, a.action_items
        FROM meetings AS m
        JOIN ai_analysis AS a ON a.meeting_id = m.id
        WHERE m.user_id = ?
        ORDER BY m.id DESC
        """,
        (user_id,),
    ).fetchall()

    speaker_columns = set()
    if table_exists(conn, "meeting_speakers"):
        speaker_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(meeting_speakers)")
        }

    for meeting in meetings:
        speaker_names = {}
        if {"speaker_label", "speaker_name", "meeting_id"}.issubset(speaker_columns):
            rows = conn.execute(
                "SELECT speaker_label, speaker_name FROM meeting_speakers WHERE meeting_id = ?",
                (meeting["meeting_id"],),
            ).fetchall()
            speaker_names = {
                str(r["speaker_label"] or "").strip().casefold(): str(r["speaker_name"] or "").strip()
                for r in rows
            }

        for item in parse_action_items(meeting["action_items"]):
            if not isinstance(item, dict):
                continue
            task_text = str(item.get("task", "") or "").strip()
            if not task_text or task_text.casefold() == "no action items identified":
                continue

            assignee = str(item.get("assignee", "") or "").strip()
            speaker_key = re.sub(
                r"^speaker\s+", "", assignee, flags=re.IGNORECASE
            ).strip().casefold()
            if speaker_names.get(speaker_key):
                assignee = speaker_names[speaker_key]

            if not assignee or assignee.casefold() in {"not specified", "unknown", "none", "null"}:
                continue
            if assignee.casefold() != user_name.casefold():
                continue

            deadline = str(item.get("deadline", "Not specified") or "Not specified").strip()

            existing = conn.execute(
                """
                SELECT id FROM tasks
                WHERE meeting_id = ? AND task = ?
                  AND LOWER(TRIM(assignee_name)) = LOWER(TRIM(?))
                  AND COALESCE(deadline, 'Not specified') = ?
                LIMIT 1
                """,
                (meeting["meeting_id"], task_text, assignee, deadline),
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO tasks (meeting_id, task, assignee_name, deadline, status) "
                    "VALUES (?, ?, ?, ?, 'Pending')",
                    (meeting["meeting_id"], task_text, assignee, deadline),
                )
    conn.commit()


def get_assigned_tasks(user_id, user_name):
    """Visible tasks assigned to the logged-in user."""
    conn = get_connection()
    try:
        if not table_exists(conn, "meetings") or not table_exists(conn, "ai_analysis"):
            return []
        ensure_tasks_table(conn)
        sync_ai_tasks(conn, user_id, user_name)

        rows = conn.execute(
            """
            SELECT t.id, t.task, t.assignee_name, t.deadline, t.status,
                   m.filename AS meeting, m.id AS meeting_id
            FROM tasks AS t
            JOIN meetings AS m ON m.id = t.meeting_id
            WHERE m.user_id = ?
              AND LOWER(TRIM(t.assignee_name)) = LOWER(TRIM(?))
              AND COALESCE(t.is_deleted, 0) = 0
            ORDER BY t.id DESC
            """,
            (user_id, user_name),
        ).fetchall()

        return [
            {
                "id": r["id"],
                "task": r["task"],
                "assignee": r["assignee_name"],
                "deadline": r["deadline"] or "Not specified",
                "status": r["status"] or "Pending",
                "meeting": r["meeting"] or f"Meeting {r['meeting_id']}",
                "meeting_id": r["meeting_id"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_task_counts(user_id, user_name):
    """Return (total, pending, completed)."""
    tasks = get_assigned_tasks(user_id, user_name)
    total = len(tasks)
    completed = sum(
        1 for t in tasks if t["status"].strip().casefold() in COMPLETED_STATUSES
    )
    return total, total - completed, completed


def update_task_status(task_id, status, user_id, user_name):
    conn = get_connection()
    try:
        ensure_tasks_table(conn)
        cursor = conn.execute(
            """
            UPDATE tasks SET status = ?
            WHERE id = ? AND COALESCE(is_deleted, 0) = 0
              AND meeting_id IN (SELECT id FROM meetings WHERE user_id = ?)
              AND LOWER(TRIM(assignee_name)) = LOWER(TRIM(?))
            """,
            (status, task_id, user_id, user_name),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_task(task_id, user_id, user_name):
    """Soft-delete a task owned by the logged-in user."""
    conn = get_connection()
    try:
        ensure_tasks_table(conn)
        cursor = conn.execute(
            """
            UPDATE tasks SET is_deleted = 1
            WHERE id = ? AND COALESCE(is_deleted, 0) = 0
              AND LOWER(TRIM(assignee_name)) = LOWER(TRIM(?))
              AND meeting_id IN (SELECT id FROM meetings WHERE user_id = ?)
            """,
            (task_id, user_name, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()