import streamlit as st

import sqlite3

import json

import ast

import re

from pathlib import Path

st.set_page_config(

    page_title="Dashboard | AI Meeting Intelligence",

    page_icon="📊",

    layout="wide"

)

# ye streamlit me user ki session related value rakhne ka mecahnism hai tumhare project me login ke baad logged_in,user_id,user_name jaise value store ki jati hai

if not st.session_state.get("logged_in", False):

    st.warning("Please login first.")

    if st.button(

        "Go to Login",

        use_container_width=True

    ):

        st.switch_page("pages/login.py")

    st.stop()

# yahan login ke baad session me saved user ki information nikali jaa rhi h

# user ki unique id

user_id = st.session_state.get("user_id")

# user ka name

user_name = st.session_state.get(

    "user_name",

    "User"

)

# user ki mail

user_email = st.session_state.get(

    "user_email",

    ""

)

# database

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "users.db"

def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    return conn

# ye function current user ki total meeting count karta hai

def get_meeting_count(user_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM meetings
            WHERE user_id = ?
        """, (user_id,))

        result = cursor.fetchone()
        return result["total"]

    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return 0

    finally:
        conn.close()

# ye function user ki total meeting show krta hai

def get_recent_meetings(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    # dasborard pe 5 recent 5 meeting upload karta hai

    cursor.execute(

        """

        SELECT

            id,

            filename,

            file_path,

            created_at

        FROM meetings

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT 5

        """,

        (user_id,)

    )

    meetings = cursor.fetchall()

    conn.close()

    return meetings

def table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


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

    # Support soft-deleted tasks if the Tasks page uses this column.
    task_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(tasks)")
    }
    if "is_deleted" not in task_columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
        )

    conn.commit()


def delete_meeting(meeting_id):
    """Delete a meeting and its related database records for the logged-in user."""
    conn = get_connection()
    try:
        meeting = conn.execute(
            "SELECT id, file_path FROM meetings WHERE id = ? AND user_id = ?",
            (meeting_id, user_id),
        ).fetchone()

        if meeting is None:
            return False, None

        file_path = meeting["file_path"]

        # Delete child records first, even if SQLite foreign-key cascading is off.
        with conn:
            for table_name in (
                "tasks",
                "ai_analysis",
                "meeting_speakers",
                "speaker_segments",
            ):
                if table_exists(conn, table_name):
                    columns = {
                        row["name"]
                        for row in conn.execute(
                            f"PRAGMA table_info({table_name})"
                        )
                    }
                    if "meeting_id" in columns:
                        conn.execute(
                            f"DELETE FROM {table_name} WHERE meeting_id = ?",
                            (meeting_id,),
                        )

            conn.execute(
                "DELETE FROM meetings WHERE id = ? AND user_id = ?",
                (meeting_id, user_id),
            )

        return True, file_path
    finally:
        conn.close()


def sync_ai_tasks(conn):
    """Sync assigned AI action items without overwriting saved task statuses."""
    if not table_exists(conn, "meetings") or not table_exists(conn, "ai_analysis"):
        return

    meetings = conn.execute(
        """
        SELECT m.id AS meeting_id, a.action_items
        FROM meetings AS m
        JOIN ai_analysis AS a ON a.meeting_id = m.id
        WHERE m.user_id = ?
        ORDER BY m.id DESC
        """,
        (user_id,),
    ).fetchall()

    has_speakers = table_exists(conn, "meeting_speakers")
    speaker_columns = set()
    if has_speakers:
        speaker_columns = {r["name"] for r in conn.execute("PRAGMA table_info(meeting_speakers)")}

    for meeting in meetings:
        speaker_names = {}
        if {"speaker_label", "speaker_name", "meeting_id"}.issubset(speaker_columns):
            rows = conn.execute(
                "SELECT speaker_label, speaker_name FROM meeting_speakers WHERE meeting_id = ?",
                (meeting["meeting_id"],),
            ).fetchall()
            speaker_names = {
                str(row["speaker_label"] or "").strip().casefold():
                str(row["speaker_name"] or "").strip()
                for row in rows
            }

        for item in parse_action_items(meeting["action_items"]):
            if not isinstance(item, dict):
                continue
            task_text = str(item.get("task", "") or "").strip()
            if not task_text or task_text.casefold() == "no action items identified":
                continue
            assignee = str(item.get("assignee", "") or "").strip()
            speaker_key = re.sub(r"^speaker\s+", "", assignee, flags=re.IGNORECASE).strip().casefold()
            if speaker_key in speaker_names and speaker_names[speaker_key]:
                assignee = speaker_names[speaker_key]
            if not assignee or assignee.casefold() in {"not specified", "unknown", "none", "null"}:
                continue
            if assignee.casefold() != (user_name or "").strip().casefold():
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
                    "INSERT INTO tasks (meeting_id, task, assignee_name, deadline, status) VALUES (?, ?, ?, ?, 'Pending')",
                    (meeting["meeting_id"], task_text, assignee, deadline),
                )
    conn.commit()


def get_task_counts(user_id, user_name):
    conn = get_connection()
    try:
        if not table_exists(conn, "meetings") or not table_exists(conn, "ai_analysis"):
            return 0, 0, 0
        ensure_tasks_table(conn)
        sync_ai_tasks(conn)
        row = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN LOWER(TRIM(COALESCE(t.status, 'Pending'))) IN ('completed', 'complete', 'done') THEN 1 ELSE 0 END) AS completed
            FROM tasks t
            JOIN meetings m ON m.id = t.meeting_id
            WHERE m.user_id = ? AND LOWER(TRIM(t.assignee_name)) = LOWER(TRIM(?))\n               AND COALESCE(t.is_deleted, 0) = 0
            """,
            (user_id, user_name),
        ).fetchone()
        total = row["total"] or 0
        completed = row["completed"] or 0
        return total, total - completed, completed
    finally:
        conn.close()


total_meetings = get_meeting_count(user_id)

total_tasks, pending_tasks, completed_tasks = get_task_counts(user_id, user_name)

recent_meetings = get_recent_meetings(

    user_id

)

with st.sidebar:

    st.title("🎙️ AI Meeting")

    st.caption(

        "Intelligence & Action Tracking"

    )

    st.divider()

    st.write("### 👤 Account")

    st.write(

        f"**{user_name}**"

    )

    if user_email:

        st.caption(user_email)

    st.divider()

    st.write("### Navigation")

    if st.button(

        "📊 Dashboard",

        use_container_width=True

    ):

        st.rerun()

    if st.button(

        "📁 My Meetings",

        use_container_width=True

    ):

        st.switch_page(

            "pages/meetings.py"

        )

    if st.button(

        "⬆️ Upload Meeting",

        use_container_width=True

    ):

        st.switch_page(

            "pages/upload.py"

        )

    if st.button(

        "📋 Tasks",

        use_container_width=True

    ):

        st.switch_page(

            "pages/task.py"

        )

    st.divider()

    if st.button(

        "🚪 Logout",

        use_container_width=True

    ):

        keys_to_remove = [

            "logged_in",

            "user_id",

            "user_name",

            "user_email",

            "user",

            "access_token",

            "selected_meeting_id",

            "task_meeting_id"

        ]

        for key in keys_to_remove:

            st.session_state.pop(

                key,

                None

            )

        st.switch_page(

            "pages/login.py"

        )

st.title(

    f"📊 Welcome, {user_name} 👋"

)

st.write(

    "Manage your meetings, transcripts, "

    "AI insights and action items from one place."

)

st.divider()

st.subheader("Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:

    # total meeting ka result

    st.metric(

        label="🎥 Total Meetings",

        value=total_meetings

    )

with col2:

    st.metric(

        label="📋 Total Tasks",

        value=total_tasks

    )

with col3:

    st.metric(

        label="⏳ Pending Tasks",

        value=pending_tasks

    )

with col4:

    st.metric(

        label="✅ Completed Tasks",

        value=completed_tasks

    )

st.divider()



st.subheader("Tasks")
view_col1, view_col2 = st.columns(2)
with view_col1:
    if st.button("📋 View Total Tasks", use_container_width=True, key="view_total_tasks"):
        st.session_state["task_page_filter"] = "all"
        st.switch_page("pages/task.py")
with view_col2:
    if st.button("⏳ View Pending Tasks", use_container_width=True, key="view_pending_tasks"):
        st.session_state["task_page_filter"] = "pending"
        st.switch_page("pages/task.py")

st.caption("Open View My Tasks to see and search your tasks. Task details are not displayed on the dashboard.")
st.divider()

st.subheader("Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:

    if st.button(

        "📁 My Meetings",

        use_container_width=True

    ):

        st.switch_page(

            "pages/meetings.py"

        )

with col2:

    if st.button(

        "⬆️ Upload Meeting",

        use_container_width=True,

        type="primary"

    ):

        st.switch_page(

            "pages/upload.py"

        )

with col3:

    if st.button(

        "📋 Manage Tasks",

        use_container_width=True

    ):

        st.switch_page(

            "pages/task.py"

        )

st.divider()

# recent meeting

st.subheader("🕒 Recent Meetings")

if not recent_meetings:

    st.info(

        "You haven't uploaded any meetings yet."

    )

    st.write(

        "Upload your first meeting to start "

        "transcription and AI analysis."

    )

    if st.button(

        "⬆️ Upload Your First Meeting",

        type="primary"

    ):

        st.switch_page(

            "pages/upload.py"

        )

else:

    st.caption(

        f"Showing your {len(recent_meetings)} "

        "most recent meetings."

    )

    for meeting in recent_meetings:

        with st.container(border=True):

            col1, col2, col3 = st.columns(

                [4, 1, 1]

            )

            with col1:

                st.markdown(

                    f"### 🎥 {meeting['filename']}"

                )

                st.caption(

                    f"Uploaded: {meeting['created_at']}"

                )

                st.caption(

                    f"Meeting ID: {meeting['id']}"

                )

            with col2:

                if st.button(

                    "View",

                    key=f"recent_view_{meeting['id']}",

                    use_container_width=True

                ):

                    st.session_state[

                        "selected_meeting_id"

                    ] = meeting["id"]

                    st.switch_page(

                        "pages/meeting_details.py"

                    )

            with col3:
                if st.button(
                    "Delete",
                    key=f"recent_delete_{meeting['id']}",
                    use_container_width=True,
                ):
                    st.session_state[f"confirm_delete_meeting_{meeting['id']}"] = True
                    st.rerun()

            confirm_key = f"confirm_delete_meeting_{meeting['id']}"
            if st.session_state.get(confirm_key, False):
                st.warning(
                    f"Delete '{meeting['filename']}' and its saved transcript, "
                    "AI analysis, speaker data, tasks, and uploaded media file? "
                    "This cannot be undone."
                )
                confirm_col, cancel_col = st.columns(2)

                with confirm_col:
                    if st.button(
                        "Yes, delete meeting",
                        key=f"confirm_yes_delete_meeting_{meeting['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        deleted, stored_file_path = delete_meeting(meeting["id"])
                        st.session_state.pop(confirm_key, None)

                        # Only remove a media file located inside the project folder.
                        if deleted and stored_file_path:
                            try:
                                project_root = Path.cwd().resolve()
                                candidate = Path(stored_file_path)
                                if not candidate.is_absolute():
                                    candidate = project_root / candidate
                                candidate = candidate.resolve()
                                if candidate.is_relative_to(project_root) and candidate.is_file():
                                    candidate.unlink()
                            except (OSError, ValueError):
                                # Database deletion succeeds even if file cleanup fails.
                                pass

                        if deleted:
                            st.success("Meeting and related records deleted.")
                        else:
                            st.error(
                                "Meeting was not found or you do not have permission to delete it."
                            )
                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        key=f"cancel_delete_meeting_{meeting['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()

# footer

st.divider()

st.caption(

    "AI Meeting Intelligence & Action Tracking"

)
