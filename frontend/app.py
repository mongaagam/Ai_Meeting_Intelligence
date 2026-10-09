import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)


import streamlit as st

login_page = st.Page(
    "pages/login.py",
    title="Login",
    icon="🔐"
)

signup_page = st.Page(
    "pages/signup.py",
    title="Create Account",
    icon="📝"
)

dashboard_page = st.Page(
    "pages/dashboard.py",
    title="Dashboard",
    icon="📊"
)


meetings_page = st.Page(
    "pages/meetings.py",
    title="My Meetings",
    icon="📁"
)


meeting_details_page = st.Page(
    "pages/meeting_details.py",
    title="Meeting Details",
    icon="🎥"
)


upload_page = st.Page(
    "pages/upload.py",
    title="Upload Meeting",
    icon="⬆️"
)


task_page = st.Page(
    "pages/task.py",
    title="Tasks",
    icon="📋"
)

pg = st.navigation(
    [
        login_page,
        signup_page,
        dashboard_page,
        meetings_page,
        meeting_details_page,
        upload_page,
        task_page
    ],
    position="hidden"
)

pg.run()