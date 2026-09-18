import streamlit as st
from pathlib import Path


upload_dir = Path("../data/uploads")


Allowed_extension = [
    "mp3",
    "wav",
    "m4a",
    "mp4",
    "mov",
    "mkv"
]

# because in computer file size are commonly stored measured in bytes
Max_Size = 200 * 1024 * 1024


st.set_page_config(
    page_title="Upload Meeting",
    page_icon="🎙️",
    layout="centered"
)


# ui
st.title("🎙️ Upload Meeting")

st.write(
    "Upload your meeting audio or video file "
    "for processing and transcription."
)

st.info(
    "Supported formats: MP3, WAV, M4A, MP4, MOV, MKV | "
    "Maximum size: 200 MB"
)


# file upload
uploaded_file = st.file_uploader(
    "Choose a meeting audio or video file",
    type=Allowed_extension
)


# meeting name
meeting_name = st.text_input(
    "Enter Meeting Name"
)


# file validation
if uploaded_file is not None:

    file_name = uploaded_file.name
    file_size = uploaded_file.size

    # Check file size
    if file_size > Max_Size:

        st.error(
            "File size exceeds the 200 MB limit."
        )

    else:

        st.success(
            "File format and size are valid."
        )

        # File information
        st.write(
            f"**Original file name:** {file_name}"
        )

        file_size_mb = file_size / (1024 * 1024)

        st.write(
            f"**File size:** {file_size_mb:.2f} MB"
        )

        st.write(
            f"**File type:** {uploaded_file.type}"
        )


        # upload button
        if st.button("Upload Meeting"):

            # Check meeting name
            if not meeting_name.strip():

                st.error(
                    "Please enter a meeting name."
                )

            else:

                try:

                    # Keep the original file extension
                    original_extension = Path(
                        uploaded_file.name
                    ).suffix

                    # Use user-provided meeting name
                    file_name = (
                        meeting_name.strip()
                        + original_extension
                    )

                    # Create the complete file path
                    file_path = upload_dir / file_name


                    # use wb because meeting file contains
                    # binary data and we need to save the file
                    with open(file_path, "wb") as f:

                        f.write(
                            uploaded_file.getbuffer()
                        )


                    st.success(
                        "Meeting uploaded successfully!"
                    )

                    st.info(
                        f"Meeting saved as: {file_name}"
                    )

                    # st.write(
                    #     f"Saved to: `{file_path}`"
                    # )


                except Exception as e:

                    st.error(
                        f"Upload failed: {str(e)}"
                    )

