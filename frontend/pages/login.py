import streamlit as st
import requests

st.set_page_config(
    page_title="Login - AI Meeting Intelligence",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ AI Meeting Intelligence")
st.subheader("Login")

email = st.text_input(
    "Email",
    placeholder="Enter your email"
)

password = st.text_input(
    "Password",
    type="password",
    placeholder="Enter your password"
)

if st.button(
    "Login",
    use_container_width=True,
    type="primary"
):

    if not email or not password:

        st.error(
            "Please enter your email and password."
        )

    else:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/auth/login",
                json={
                    "email": email,
                    "password": password
                }
            )

            if response.status_code == 200:

                data = response.json()

                user = data["user"]

            #    save login information
                st.session_state["access_token"] = (
                    data["access_token"]
                )

                st.session_state["user"] = user

                st.session_state["user_id"] = (
                    user["id"]
                )

                st.session_state["user_name"] = (
                    user["full_name"]
                )

                st.session_state["user_email"] = (
                    user["email"]
                )

                st.session_state["logged_in"] = True

                st.success(
                    f"Welcome, {user['full_name']}!"
                )

                # Go to Dashboard
                st.switch_page(
                    "pages/dashboard.py"
                )

            elif response.status_code == 401:

                st.error(
                    "Invalid email or password."
                )

            else:

                st.error(
                    "Something went wrong."
                )

        except requests.exceptions.ConnectionError:

            st.error(
                "Cannot connect to FastAPI server. "
                "Please make sure FastAPI is running."
            )


st.write("")


if st.button(
    "Create an Account",
    use_container_width=True
):

    st.switch_page(
        "pages/signup.py"
    )