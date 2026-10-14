import streamlit as st
import requests

st.set_page_config(
    page_title="Create Account - AI Meeting Intelligence",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ AI Meeting Intelligence")
st.subheader("Create an Account")

full_name = st.text_input(
    "Full Name",
    placeholder="Enter your full name"
)

email = st.text_input(
    "Email",
    placeholder="Enter your email"
)

password = st.text_input(
    "Password",
    type="password",
    placeholder="Create a password"
)

confirm_password = st.text_input(
    "Confirm Password",
    type="password",
    placeholder="Confirm your password"
)

if st.button(
    "Create Account",
    use_container_width=True,
    type="primary"
):
    if not full_name or not email or not password:
        st.error("Please fill in all fields.")

    elif password != confirm_password:
        st.error("Passwords do not match.")

    else:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/auth/signup",
                json={
                    "full_name": full_name,
                    "email": email,
                    "password": password
                }
            )

            if response.status_code == 200:
                st.success("Account created successfully!")
                st.info("Now go to Login and login with your credentials.")

            elif response.status_code == 400:
                data = response.json()
                st.error(
                    data.get(
                        "detail",
                        "Unable to create account."
                    )
                )

            else:
                st.error("Something went wrong.")

        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to FastAPI server. "
                "Please make sure FastAPI is running."
            )

st.write("")

if st.button(
    "Back to Login",
    use_container_width=True
):
    st.switch_page("pages/login.py")