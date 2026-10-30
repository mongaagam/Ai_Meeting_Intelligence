import ast
import json
import re
import sqlite3
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="My Tasks",
    page_icon="📋",
    layout="wide",
)

# -------------------- AUTHENTICATION --------------------

if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")

    if st.button("Go to Login"):
        st.switch_page("pages/login.py")

    st.stop()

user_id = st.session_state.get("user_id")
user_name = str(
    st.session_state.get("user_name", "User") or "User"
).strip()

DB_PATH = Path("data/users.db")


# -------------------- DATABASE --------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    return conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone() is not None


def ensure_tasks_table(conn):
    """Create the tasks table and add soft-delete support."""
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
            FOREIGN KEY (meeting_id)
                REFERENCES meetings(id) ON DELETE CASCADE
        )
        """
    )

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(tasks)"
        ).fetchall()
    }

    if "is_deleted" not in columns:
        conn.execute(
            """
            ALTER TABLE tasks
            ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0
            """
        )

    conn.commit()


# -------------------- AI ACTION ITEM PARSING --------------------

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


# -------------------- SYNC AI TASKS --------------------

def sync_ai_tasks(conn):
    """
    Import assigned AI action items without overwriting saved statuses.
    Previously deleted tasks are not recreated.
    """
    if not table_exists(conn, "meetings"):
        return

    if not table_exists(conn, "ai_analysis"):
        return

    meetings = conn.execute(
        """
        SELECT
            m.id AS meeting_id,
            m.filename,
            a.action_items
        FROM meetings AS m
        JOIN ai_analysis AS a
            ON a.meeting_id = m.id
        WHERE m.user_id = ?
        ORDER BY m.id DESC
        """,
        (user_id,),
    ).fetchall()

    has_speakers = table_exists(conn, "meeting_speakers")
    speaker_columns = set()

    if has_speakers:
        speaker_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(meeting_speakers)"
            ).fetchall()
        }

    for meeting in meetings:
        speaker_names = {}

        if {
            "speaker_label",
            "speaker_name",
            "meeting_id",
        }.issubset(speaker_columns):
            rows = conn.execute(
                """
                SELECT speaker_label, speaker_name
                FROM meeting_speakers
                WHERE meeting_id = ?
                """,
                (meeting["meeting_id"],),
            ).fetchall()

            speaker_names = {
                str(row["speaker_label"] or "")
                .strip()
                .casefold(): str(row["speaker_name"] or "").strip()
                for row in rows
            }

        for item in parse_action_items(meeting["action_items"]):
            if not isinstance(item, dict):
                continue

            task_text = str(
                item.get("task", "") or ""
            ).strip()

            if (
                not task_text
                or task_text.casefold() == "no action items identified"
            ):
                continue

            assignee = str(
                item.get("assignee", "") or ""
            ).strip()

            speaker_key = re.sub(
                r"^speaker\s+",
                "",
                assignee,
                flags=re.IGNORECASE,
            ).strip().casefold()

            if speaker_key in speaker_names and speaker_names[speaker_key]:
                assignee = speaker_names[speaker_key]

            if not assignee or assignee.casefold() in {
                "not specified",
                "unknown",
                "none",
                "null",
            }:
                continue

            # Only sync tasks assigned to the logged-in user.
            if assignee.casefold() != user_name.casefold():
                continue

            deadline = str(
                item.get("deadline", "Not specified")
                or "Not specified"
            ).strip()

            # Do not recreate a previously deleted task.
            existing = conn.execute(
                """
                SELECT id
                FROM tasks
                WHERE meeting_id = ?
                  AND task = ?
                  AND LOWER(TRIM(assignee_name)) =
                      LOWER(TRIM(?))
                  AND COALESCE(deadline, 'Not specified') = ?
                LIMIT 1
                """,
                (
                    meeting["meeting_id"],
                    task_text,
                    assignee,
                    deadline,
                ),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        meeting_id,
                        task,
                        assignee_name,
                        deadline,
                        status
                    )
                    VALUES (?, ?, ?, ?, 'Pending')
                    """,
                    (
                        meeting["meeting_id"],
                        task_text,
                        assignee,
                        deadline,
                    ),
                )

    conn.commit()


# -------------------- GET ASSIGNED TASKS --------------------

def get_assigned_tasks():
    """Return visible tasks assigned to the logged-in user."""
    conn = get_connection()

    try:
        if not table_exists(conn, "meetings"):
            return []

        ensure_tasks_table(conn)

        if not table_exists(conn, "ai_analysis"):
            return []

        sync_ai_tasks(conn)

        rows = conn.execute(
            """
            SELECT
                t.id,
                t.task,
                t.assignee_name,
                t.deadline,
                t.status,
                m.filename AS meeting,
                m.id AS meeting_id
            FROM tasks AS t
            JOIN meetings AS m
                ON m.id = t.meeting_id
            WHERE m.user_id = ?
              AND LOWER(TRIM(t.assignee_name)) =
                  LOWER(TRIM(?))
              AND COALESCE(t.is_deleted, 0) = 0
            ORDER BY t.id DESC
            """,
            (user_id, user_name),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "task": row["task"],
                "assignee": row["assignee_name"],
                "deadline": row["deadline"] or "Not specified",
                "status": row["status"] or "Pending",
                "meeting": (
                    row["meeting"]
                    or f"Meeting {row['meeting_id']}"
                ),
                "meeting_id": row["meeting_id"],
            }
            for row in rows
        ]

    finally:
        conn.close()


# -------------------- UPDATE TASK STATUS --------------------

def update_task_status(task_id, status):
    """Update a task only if it belongs to the current user."""
    conn = get_connection()

    try:
        ensure_tasks_table(conn)

        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = ?
            WHERE id = ?
              AND COALESCE(is_deleted, 0) = 0
              AND meeting_id IN (
                  SELECT id
                  FROM meetings
                  WHERE user_id = ?
              )
              AND LOWER(TRIM(assignee_name)) =
                  LOWER(TRIM(?))
            """,
            (status, task_id, user_id, user_name),
        )

        conn.commit()
        return cursor.rowcount > 0

    finally:
        conn.close()


# -------------------- DELETE TASK --------------------

def delete_task(task_id):
    """
    Soft-delete a task only if it belongs to the logged-in user.
    The record remains in the database but is hidden from the UI.
    """
    conn = get_connection()

    try:
        ensure_tasks_table(conn)

        cursor = conn.execute(
            """
            UPDATE tasks
            SET is_deleted = 1
            WHERE id = ?
              AND COALESCE(is_deleted, 0) = 0
              AND LOWER(TRIM(assignee_name)) =
                  LOWER(TRIM(?))
              AND meeting_id IN (
                  SELECT id
                  FROM meetings
                  WHERE user_id = ?
              )
            """,
            (task_id, user_name, user_id),
        )

        conn.commit()
        return cursor.rowcount > 0

    finally:
        conn.close()


# -------------------- PAGE HEADER --------------------

st.title("📋 View My Tasks")

st.write(
    f"Tasks explicitly assigned to **{user_name}** "
    "from your processed meetings."
)

st.caption(
    "Task status changes are saved permanently. "
    "You can search, complete, or delete your tasks."
)

st.divider()


# -------------------- LOAD TASKS AND FILTER --------------------

all_tasks = get_assigned_tasks()

requested_filter = st.session_state.pop(
    "task_page_filter",
    "all",
)

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "📋 View Total Tasks",
        use_container_width=True,
        key="task_page_all",
    ):
        requested_filter = "all"

with col2:
    if st.button(
        "⏳ View Pending Tasks",
        use_container_width=True,
        key="task_page_pending",
    ):
        requested_filter = "pending"


if requested_filter == "pending":
    visible_tasks = [
        task
        for task in all_tasks
        if task["status"].strip().casefold()
        not in {"completed", "complete", "done"}
    ]

    st.subheader("⏳ Pending Tasks")

else:
    visible_tasks = all_tasks
    st.subheader("📋 All Assigned Tasks")


search_term = st.text_input(
    "Search tasks",
    placeholder="Search task, meeting, deadline, or status...",
    key="my_tasks_search",
).strip().casefold()

if search_term:
    visible_tasks = [
        task
        for task in visible_tasks
        if search_term in task["task"].casefold()
        or search_term in task["meeting"].casefold()
        or search_term in task["deadline"].casefold()
        or search_term in task["status"].casefold()
        or search_term in task["assignee"].casefold()
    ]


st.caption(
    f"Showing {len(visible_tasks)} task(s). "
    f"Total assigned to you: {len(all_tasks)}."
)


# -------------------- DISPLAY TASKS --------------------

if visible_tasks:
    for index, task in enumerate(visible_tasks, start=1):
        with st.container(border=True):
            st.markdown(
                f"**{index}. {task['task']}**"
            )

            st.caption(
                f"Meeting: {task['meeting']} · "
                f"Meeting ID: {task['meeting_id']}"
            )

            left, right = st.columns(2)

            with left:
                st.write(f"**Assignee:** {task['assignee']}")
                st.write(f"**Deadline:** {task['deadline']}")

            with right:
                st.write(f"**Status:** {task['status']}")

                is_completed = (
                    task["status"].strip().casefold()
                    in {"completed", "complete", "done"}
                )

                if not is_completed:
                    if st.button(
                        "✅ Mark as Completed",
                        key=f"complete_task_{task['id']}",
                        use_container_width=True,
                    ):
                        if update_task_status(
                            task["id"],
                            "Completed",
                        ):
                            st.success("Task marked as completed.")
                        else:
                            st.error(
                                "Task not found or access denied."
                            )

                        st.rerun()

                else:
                    st.success("Completed")

                # Ask for confirmation before deleting.
                confirm_key = (
                    f"confirm_delete_task_{task['id']}"
                )

                if st.button(
                    "🗑️ Delete Task",
                    key=f"delete_task_{task['id']}",
                    use_container_width=True,
                ):
                    st.session_state[confirm_key] = True

                if st.session_state.get(confirm_key, False):
                    st.warning(
                        "Are you sure you want to delete "
                        "this task?"
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:
                        if st.button(
                            "Confirm Delete",
                            key=f"confirm_task_delete_{task['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            if delete_task(task["id"]):
                                st.session_state.pop(
                                    confirm_key,
                                    None,
                                )
                                st.success("Task deleted.")
                            else:
                                st.error(
                                    "Task not found or access denied."
                                )

                            st.rerun()

                    with cancel_col:
                        if st.button(
                            "Cancel",
                            key=f"cancel_task_delete_{task['id']}",
                            use_container_width=True,
                        ):
                            st.session_state.pop(
                                confirm_key,
                                None,
                            )
                            st.rerun()

else:
    st.info(
        "No assigned tasks match this view. Check that AI "
        "action_items explicitly name your logged-in account "
        "as the assignee."
    )


# -------------------- FOOTER --------------------

st.divider()

if st.button(
    "⬅️ Back to Dashboard",
    use_container_width=False,
):
    st.switch_page("pages/dashboard.py")
