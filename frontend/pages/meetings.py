import streamlit as st
import sqlite3
from pathlib import Path


st.set_page_config(
    page_title="My Meetings",
    page_icon="📁",
    layout="wide"
)

# login check
if not st.session_state.get(
    "logged_in",
    False
):

    st.warning(
        "Please login first."
    )

    st.stop()

# user

user_id = st.session_state.get(
    "user_id"
)

user_name = st.session_state.get(
    "user_name",
    "User"
)


# ==================================================
# DATABASE
# ==================================================

DB_PATH = Path(
    "data/users.db"
)


def get_connection():

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def get_user_meetings(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            filename,
            meeting_name,
            file_path,
            created_at
        FROM meetings
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    meetings = cursor.fetchall()

    conn.close()

    return meetings

# page
st.title("📁 My Meetings")

st.write(
    f"Meetings uploaded by **{user_name}**"
)

st.divider()


meetings = get_user_meetings(
    user_id
)


if not meetings:

    st.info(
        "You have not uploaded any meetings yet."
    )

else:

    st.success(
        f"{len(meetings)} meetings found."
    )

    for meeting in meetings:

        with st.container(
            border=True
        ):

            col1, col2, col3 = st.columns(
                [5, 2, 1]
            )

            with col1:

                st.subheader(
                    f"🎥 {meeting['meeting_name']}"
                )

                st.caption(
                    f"Uploaded: {meeting['created_at']}"
                )

            with col2:

                st.write("Meeting ID")

                st.write(
                    f"#{meeting['id']}"
                )

            with col3:

                if st.button(
                    "View",
                    key=f"meeting_{meeting['id']}"
                ):

                    st.session_state[
                        "selected_meeting_id"
                    ] = meeting["id"]

                    st.switch_page(
                        "pages/meeting_details.py"
                    )