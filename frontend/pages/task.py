import streamlit as st
import sqlite3
from pathlib import Path
from datetime import date


st.set_page_config(
    page_title="Tasks",
    page_icon="📋",
    layout="wide"
)


if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.stop()


user_id = st.session_state.get("user_id")


DB_PATH = Path("data/users.db")


st.title("📋 Task Management")

st.write(
    "Assign and track meeting action items."
)

st.divider()


# -----------------------------
# Assign Task
# -----------------------------

st.subheader("➕ Assign New Task")


task = st.text_input(
    "Task",
    placeholder="Enter task description"
)


assignee = st.text_input(
    "Assignee",
    placeholder="Enter assignee name"
)


deadline = st.date_input(
    "Deadline",
    value=date.today()
)


status = st.selectbox(
    "Status",
    [
        "Pending",
        "In Progress",
        "Completed"
    ]
)


if st.button(
    "Assign Task",
    type="primary"
):

    if not task:

        st.error(
            "Please enter a task."
        )

    elif not assignee:

        st.error(
            "Please enter an assignee."
        )

    else:

        st.success(
            "Task assigned successfully!"
        )