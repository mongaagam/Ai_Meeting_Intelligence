import streamlit as st
import sqlite3
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
DB_PATH = Path("data/users.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ye function current user ki total meeting count karta hai
def get_meeting_count(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM meetings
        WHERE user_id = ?
        """,
        (user_id,)
    )

    result = cursor.fetchone()
    conn.close()
    return result["total"]

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


def get_task_counts(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'tasks'
        """
    )

    table_exists = cursor.fetchone()

    if not table_exists:
        conn.close()
        return 0, 0


    cursor.execute(
        "PRAGMA table_info(tasks)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]


    if "user_id" in columns:

        if "status" in columns:

            cursor.execute(
                # pending aur completed status edentify krna
                """
                SELECT
                    SUM(
                        CASE
                            WHEN LOWER(status) IN
                            ('pending', 'todo', 'to do')
                            THEN 1
                            ELSE 0
                        END
                    ) AS pending,
                  
                    SUM(
                        CASE
                            WHEN LOWER(status) IN
                            ('completed', 'complete', 'done')
                            THEN 1
                            ELSE 0
                        END
                    ) AS completed

                FROM tasks

                WHERE user_id = ?
                """,
                (user_id,)
            )

        else:

            cursor.execute(
                """
                SELECT COUNT(*) AS pending
                FROM tasks
                WHERE user_id = ?
                """,
                (user_id,)
            )

            result = cursor.fetchone()

            conn.close()

            return result["pending"] or 0, 0

    else:

        if "status" in columns:

            cursor.execute(
                """
                SELECT
                    SUM(
                        CASE
                            WHEN LOWER(status) IN
                            ('pending', 'todo', 'to do')
                            THEN 1
                            ELSE 0
                        END
                    ) AS pending,

                    SUM(
                        CASE
                            WHEN LOWER(status) IN
                            ('completed', 'complete', 'done')
                            THEN 1
                            ELSE 0
                        END
                    ) AS completed

                FROM tasks
                """
            )

        else:

            cursor.execute(
                """
                SELECT COUNT(*) AS pending
                FROM tasks
                """
            )

            result = cursor.fetchone()

            conn.close()

            return result["pending"] or 0, 0


    result = cursor.fetchone()

    conn.close()

    pending = result["pending"] or 0
    completed = result["completed"] or 0

    return pending, completed


total_meetings = get_meeting_count(user_id)

pending_tasks, completed_tasks = get_task_counts(
    user_id
)

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

col1, col2, col3 = st.columns(3)

with col1:
    # total meeting ka result
    st.metric(
        label="🎥 Total Meetings",
        value=total_meetings
    )

with col2:

    st.metric(
        # pending meeting ka result
        label="⏳ Pending Tasks",
        value=pending_tasks
    )

with col3:

    st.metric(
        # completed task ka result
        label="✅ Completed Tasks",
        value=completed_tasks
    )


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

            col1, col2 = st.columns(
                [5, 1]
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


# footer
st.divider()
st.caption(
    "AI Meeting Intelligence & Action Tracking"
)
