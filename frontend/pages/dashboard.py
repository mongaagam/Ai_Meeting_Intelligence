import requests
import streamlit as st

API_BASE_URL = "http://13.233.34.230:8000"
REQUEST_TIMEOUT = 15
# Set this to your real tasks route from http://13.233.34.230:8000/docs
# (e.g. "/tasks", "/tasks/my", "/action-items/"). Use None to hide task counts.
TASKS_ENDPOINT = "/tasks/"
COMPLETED_STATUSES = {"completed", "complete", "done"}


# ---------------------------------------------------------------------------
# Auth guard (must run before anything else touches session data)
# ---------------------------------------------------------------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    if st.button("Go to Login", use_container_width=True):
        st.switch_page("pages/login.py")
    st.stop()

user_id = st.session_state.get("user_id")
user_name = st.session_state.get("user_name", "User")
user_email = st.session_state.get("user_email", "")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def get_auth_headers():
    """Return the Authorization header for the logged-in user, or None."""
    token = st.session_state.get("access_token")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def api_request(method, path, quiet=False, **kwargs):
    """Call the FastAPI backend with auth. Returns the response or None."""
    headers = get_auth_headers()
    if not headers:
        st.error("Your session has expired. Please log in again.")
        return None
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        if quiet:
            st.caption(f"⚠️ Task counts unavailable ({path}: check TASKS_ENDPOINT).")
        else:
            st.error(f"Request to {path} failed: {e}")
        return None


def get_meeting_count():
    response = api_request("GET", "/meetings/count")
    if response is None:
        return 0
    return response.json().get("total_meetings", 0)


def get_recent_meetings(limit=5):
    response = api_request("GET", "/meetings/")
    if response is None:
        return []
    meetings = response.json().get("meetings", [])
    if not isinstance(meetings, list):
        return []
    # Newest first, in case the API does not already sort.
    meetings = sorted(meetings, key=lambda m: m.get("id", 0), reverse=True)
    return meetings[:limit]


def get_task_counts():
    """Return (total, pending, completed) for the logged-in user's tasks.

    ASSUMPTION: GET /tasks/ returns {"tasks": [{"status": ..., "is_deleted": ...}, ...]}
    scoped to the authenticated user. Adjust if your backend differs.
    """
    if not TASKS_ENDPOINT:
        return 0, 0, 0
    response = api_request("GET", TASKS_ENDPOINT, quiet=True)
    if response is None:
        return 0, 0, 0
    data = response.json()
    tasks = data if isinstance(data, list) else data.get("tasks", [])
    if not isinstance(tasks, list):
        return 0, 0, 0

    tasks = [t for t in tasks if not t.get("is_deleted")]
    total = len(tasks)
    completed = sum(
        1
        for t in tasks
        if str(t.get("status") or "Pending").strip().lower() in COMPLETED_STATUSES
    )
    return total, total - completed, completed


def delete_meeting(meeting_id):
    """Delete a meeting (backend removes related data and media).

    ASSUMPTION: DELETE /meetings/{id} exists and enforces ownership.
    """
    return api_request("DELETE", f"/meetings/{meeting_id}") is not None


# ---------------------------------------------------------------------------
# Data for the page
# ---------------------------------------------------------------------------
total_meetings = get_meeting_count()
total_tasks, pending_tasks, completed_tasks = get_task_counts()
recent_meetings = get_recent_meetings()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🎙️ AI Meeting")
    st.caption("Intelligence & Action Tracking")
    st.divider()

    st.write("### 👤 Account")
    st.write(f"**{user_name}**")
    if user_email:
        st.caption(user_email)
    st.divider()

    st.write("### Navigation")
    if st.button("📊 Dashboard", use_container_width=True):
        st.rerun()
    if st.button("📁 My Meetings", use_container_width=True):
        st.switch_page("pages/meetings.py")
    if st.button("⬆️ Upload Meeting", use_container_width=True):
        st.switch_page("pages/upload.py")
    if st.button("📋 Tasks", use_container_width=True):
        st.switch_page("pages/task.py")
    st.divider()

    if st.button("🚪 Logout", use_container_width=True):
        for key in (
            "logged_in",
            "user_id",
            "user_name",
            "user_email",
            "user",
            "access_token",
            "selected_meeting_id",
            "task_meeting_id",
        ):
            st.session_state.pop(key, None)
        st.switch_page("pages/login.py")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------
st.title(f"📊 Welcome, {user_name} 👋")
st.write(
    "Manage your meetings, transcripts, AI insights and action items "
    "from one place."
)
st.divider()

st.subheader("Overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("🎥 Total Meetings", total_meetings)
m2.metric("📋 Total Tasks", total_tasks)
m3.metric("⏳ Pending Tasks", pending_tasks)
m4.metric("✅ Completed Tasks", completed_tasks)
st.divider()

st.subheader("Tasks")
t1, t2 = st.columns(2)
with t1:
    if st.button("📋 View Total Tasks", use_container_width=True, key="view_total_tasks"):
        st.session_state["task_page_filter"] = "all"
        st.switch_page("pages/task.py")
with t2:
    if st.button("⏳ View Pending Tasks", use_container_width=True, key="view_pending_tasks"):
        st.session_state["task_page_filter"] = "pending"
        st.switch_page("pages/task.py")
st.caption(
    "Open View My Tasks to see and search your tasks. "
    "Task details are not displayed on the dashboard."
)
st.divider()

st.subheader("Quick Actions")
q1, q2, q3 = st.columns(3)
with q1:
    if st.button("📁 My Meetings", use_container_width=True, key="qa_meetings"):
        st.switch_page("pages/meetings.py")
with q2:
    if st.button("⬆️ Upload Meeting", use_container_width=True, type="primary", key="qa_upload"):
        st.switch_page("pages/upload.py")
with q3:
    if st.button("📋 Manage Tasks", use_container_width=True, key="qa_tasks"):
        st.switch_page("pages/task.py")
st.divider()

# ---------------------------------------------------------------------------
# Recent meetings
# ---------------------------------------------------------------------------
st.subheader("🕒 Recent Meetings")

if not recent_meetings:
    st.info("You haven't uploaded any meetings yet.")
    st.write("Upload your first meeting to start transcription and AI analysis.")
    if st.button("⬆️ Upload Your First Meeting", type="primary", key="upload_first"):
        st.switch_page("pages/upload.py")
else:
    st.caption(f"Showing your {len(recent_meetings)} most recent meetings.")

    for meeting in recent_meetings:
        meeting_id = meeting["id"]
        filename = meeting.get("filename", "Untitled")
        confirm_key = f"confirm_delete_meeting_{meeting_id}"

        with st.container(border=True):
            info_col, view_col, delete_col = st.columns([4, 1, 1])

            with info_col:
                st.markdown(f"### 🎥 {filename}")
                st.caption(f"Uploaded: {meeting.get('created_at', 'Unknown')}")
                st.caption(f"Meeting ID: {meeting_id}")

            with view_col:
                if st.button("View", key=f"recent_view_{meeting_id}", use_container_width=True):
                    st.session_state["selected_meeting_id"] = meeting_id
                    st.switch_page("pages/meeting_details.py")

            with delete_col:
                if st.button("Delete", key=f"recent_delete_{meeting_id}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()

            if st.session_state.get(confirm_key, False):
                st.warning(
                    f"Delete '{filename}' and its saved transcript, AI analysis, "
                    "speaker data, tasks, and uploaded media file? "
                    "This cannot be undone."
                )
                yes_col, no_col = st.columns(2)

                with yes_col:
                    if st.button(
                        "Yes, delete meeting",
                        key=f"confirm_yes_delete_meeting_{meeting_id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state.pop(confirm_key, None)
                        if delete_meeting(meeting_id):
                            st.success("Meeting and related records deleted.")
                            st.rerun()

                with no_col:
                    if st.button(
                        "Cancel",
                        key=f"cancel_delete_meeting_{meeting_id}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()

st.divider()
st.caption("AI Meeting Intelligence & Action Tracking")