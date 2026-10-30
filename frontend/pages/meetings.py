import streamlit as st
import sqlite3
from pathlib import Path
import re

st.set_page_config(page_title="My Meetings", page_icon="📁", layout="wide")

if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.stop()

user_id = st.session_state.get("user_id")
user_name = st.session_state.get("user_name", "User")
DB_PATH = Path("data/users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_meetings(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        meeting_columns = {
            row["name"] for row in cursor.execute("PRAGMA table_info(meetings)").fetchall()
        }
        if not meeting_columns:
            return []

        name_expr = "m.meeting_name" if "meeting_name" in meeting_columns else "m.filename"
        analysis_tables = {
            row["name"] for row in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "ai_analysis" in analysis_tables:
            query = f"""
                SELECT m.id, m.filename, {name_expr} AS meeting_name,
                       m.file_path, m.created_at, a.transcript
                FROM meetings AS m
                LEFT JOIN ai_analysis AS a ON a.meeting_id = m.id
                WHERE m.user_id = ?
                ORDER BY m.created_at DESC, m.id DESC
            """
        else:
            query = f"""
                SELECT m.id, m.filename, {name_expr} AS meeting_name,
                       m.file_path, m.created_at, NULL AS transcript
                FROM meetings AS m
                WHERE m.user_id = ?
                ORDER BY m.created_at DESC, m.id DESC
            """
        return cursor.execute(query, (user_id,)).fetchall()
    finally:
        conn.close()


def find_match_snippet(transcript, search_term, context_chars=90):
    if not transcript:
        return None
    match = re.search(re.escape(search_term), transcript, flags=re.IGNORECASE)
    if not match:
        return None
    start = max(0, match.start() - context_chars)
    end = min(len(transcript), match.end() + context_chars)
    snippet = transcript[start:end].replace("\\n", " ").replace("\n", " ")
    if start > 0:
        snippet = "…" + snippet
    if end < len(transcript):
        snippet += "…"
    return snippet


st.title("📁 My Meetings")
st.write(f"Meetings uploaded by **{user_name}**")
st.divider()

search_term = st.text_input(
    "🔎 Search across meeting transcripts",
    placeholder="Type a word or phrase, e.g. faster whisper, deadline, Anant...",
    key="meeting_transcript_search",
).strip()

meetings = get_user_meetings(user_id)

if not meetings:
    st.info("You have not uploaded any meetings yet.")
else:
    if search_term:
        matching_meetings = []
        term = search_term.casefold()
        for meeting in meetings:
            transcript = meeting["transcript"] or ""
            filename = meeting["filename"] or ""
            meeting_name = meeting["meeting_name"] or ""
            transcript_match = term in transcript.casefold()
            name_match = term in filename.casefold() or term in meeting_name.casefold()
            if transcript_match or name_match:
                matching_meetings.append((meeting, transcript_match, name_match))

        st.success(f"{len(matching_meetings)} meeting(s) matched '{search_term}'.")
        if not matching_meetings:
            st.info("No matching meetings found. Clear the search to see all meetings.")

        for meeting, transcript_match, name_match in matching_meetings:
            with st.container(border=True):
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    display_name = (
                        meeting["meeting_name"]
                        or meeting["filename"]
                        or f"Meeting {meeting['id']}"
                    )
                    st.subheader(f"🎥 {display_name}")
                    st.caption(f"Uploaded: {meeting['created_at']}")
                    if transcript_match:
                        snippet = find_match_snippet(meeting["transcript"] or "", search_term)
                        if snippet:
                            st.markdown("**Transcript match**")
                            st.write(snippet)
                    elif name_match:
                        st.caption("Matched meeting name or filename.")
                with col2:
                    st.write("Meeting ID")
                    st.write(f"#{meeting['id']}")
                with col3:
                    if st.button("View", key=f"search_meeting_{meeting['id']}"):
                        st.session_state["selected_meeting_id"] = meeting["id"]
                        st.switch_page("pages/meeting_details.py")
    else:
        st.success(f"{len(meetings)} meetings found.")
        for meeting in meetings:
            with st.container(border=True):
                col1, col2, col3 = st.columns([5, 2, 1])
                with col1:
                    display_name = (
                        meeting["meeting_name"]
                        or meeting["filename"]
                        or f"Meeting {meeting['id']}"
                    )
                    st.subheader(f"🎥 {display_name}")
                    st.caption(f"Uploaded: {meeting['created_at']}")
                with col2:
                    st.write("Meeting ID")
                    st.write(f"#{meeting['id']}")
                with col3:
                    if st.button("View", key=f"meeting_{meeting['id']}"):
                        st.session_state["selected_meeting_id"] = meeting["id"]
                        st.switch_page("pages/meeting_details.py")
