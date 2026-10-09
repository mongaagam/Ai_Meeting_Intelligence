import sqlite3
from pathlib import Path
import streamlit as st
from backend.db.database import init_db
from backend.services.ai_analysis import process_meeting

st.set_page_config(
    page_title="Upload Meeting",
    page_icon="🎥",
    layout="wide"
)

init_db()

if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.stop()

user_id = st.session_state.get("user_id")

if not user_id:
    st.error("User session not found.")
    st.stop()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

st.title("🎥 Upload Meeting")

st.write(
    "Upload your meeting recording to generate "
    "the transcript and AI meeting analysis."
)

meeting_name = st.text_input(
    "Meeting Name",
    placeholder="e.g. Weekly Project Meeting"
)

uploaded_file = st.file_uploader(
    "Choose a meeting recording",
    type=["mp3", "wav", "m4a", "mp4", "mov"]
)

if uploaded_file is not None:
    st.write(f"**Selected file:** {uploaded_file.name}")

    file_path = UPLOAD_DIR / uploaded_file.name

    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    except Exception as e:
        st.error(f"Could not save file: {e}")
        st.stop()

    if st.button(
        "🚀 Process Meeting",
        use_container_width=True
    ):
        conn = sqlite3.connect("data/users.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO meetings (
                    user_id,
                    meeting_name,
                    filename,
                    file_path,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    meeting_name.strip(),
                    uploaded_file.name,
                    str(file_path),
                    "uploaded"
                )
            )

            meeting_id = cursor.lastrowid
            conn.commit()

        except Exception as e:
            conn.rollback()
            conn.close()
            st.error(f"Could not create meeting record: {e}")
            st.stop()

        conn.close()

        st.session_state["processing_meeting_id"] = meeting_id

        st.divider()
        st.header("⚙️ Processing Meeting")

        progress = st.progress(0)
        status_text = st.empty()

        try:
            status_text.info("🎙️ Starting Whisper transcription...")
            progress.progress(15)

            status_text.info("📝 Generating speaker transcript...")
            progress.progress(30)

            status_text.info("👥 Detecting speakers...")
            progress.progress(50)

            result = process_meeting(
                meeting_id,
                str(file_path)
            )

            progress.progress(80)
            status_text.info(" Generating AI meeting analysis...")

            progress.progress(100)
            status_text.success("✅ Meeting processing completed!")

            st.session_state["processing_result"] = result
            st.session_state["selected_meeting_id"] = meeting_id

            st.rerun()

        except Exception as e:
            progress.progress(100)
            status_text.error("❌ Meeting processing failed.")
            st.error(f"Error: {e}")
            st.info("Please check the terminal logs for the detailed error.")
            st.stop()

result = st.session_state.get("processing_result")

if result:
    st.divider()
    st.success(" Meeting processed successfully!")

    st.header("📝 Transcript")

    transcript = result.get("transcript", "")

    if transcript:
        st.text_area(
            "Speaker Transcript",
            transcript,
            height=500,
            label_visibility="collapsed"
        )
    else:
        st.info("Transcript is not available.")

    st.divider()
    st.header("🤖 AI Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Summary")
        summary = result.get("summary", "")

        if summary:
            st.write(summary)
        else:
            st.info("Summary is not available.")

    with col2:
        st.subheader(" Decisions")
        decisions = result.get("decisions", "")

        if decisions:
            st.write(decisions)
        else:
            st.info("No decisions identified.")

    st.subheader(" Key Topics")
    key_topics = result.get("key_topics", "")

    if key_topics:
        st.write(key_topics)
    else:
        st.info("No key topics identified.")

    st.subheader("Action Items")
    action_items = result.get("action_items", "")

    if action_items:
        import json
        import pandas as pd

        try:
            if isinstance(action_items, str):
                action_items_data = json.loads(action_items)
            else:
                action_items_data = action_items

            if action_items_data:
                action_items_df = pd.DataFrame(action_items_data)

                if "status" not in action_items_df.columns:
                    action_items_df["status"] = "Pending"

                for column in ["task", "assignee", "deadline"]:
                    if column not in action_items_df.columns:
                        action_items_df[column] = "Not specified"

                action_items_df = action_items_df[
                    ["task", "assignee", "deadline", "status"]
                ]

                action_items_df.columns = [
                    "Task",
                    "Assignee",
                    "Deadline",
                    "Status"
                ]

                st.dataframe(
                    action_items_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No action items identified.")

        except Exception:
            st.write(action_items)
    else:
        st.info("No action items identified.")

    st.subheader(" Meeting Insights")
    insights = result.get("insights", "")

    if insights:
        st.write(insights)
    else:
        st.info("No meeting insights available.")

    st.divider()

    if st.button(
        "📄 Open Meeting Details",
        use_container_width=True
    ):
        st.switch_page("pages/meeting_details.py")