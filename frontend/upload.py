import streamlit as st
from pathlib import Path

upload_dir =Path("data/uploads")

Allowed_extension= [
    "mp3",
    "wav",
    "m4a",
    "mp4",
    "mov",
    "mkv"
]

# beacuse in computer file size are commonly stored measured in bytes
Max_Size= 500 * 1024 * 1024 

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
    "Maximum size: 500 MB"
)


# file upload
uploaded_file = st.file_uploader(
    "Choose a meeting audio or video file",
    type=Allowed_extension
)


# file validation
if uploaded_file is not None:

    file_name = uploaded_file.name
    file_size = uploaded_file.size

    # Check file size
    if file_size > Max_Size:

        st.error(
            "❌ File size exceeds the 500 MB limit."
        )

    else:

        st.success("✅ File format and size are valid.")

        # File information
        st.write(f"**File name:** {file_name}")

        file_size_mb = file_size / (1024 * 1024)

        st.write(
            f"**File size:** {file_size_mb:.2f} MB"
        )

        st.write(
            f"**File type:** {uploaded_file.type}"
        )

        # uplodd button
        if st.button(
            "Upload Meeting"
        ):

            try:
                file_path = upload_dir/file_name

                # use wb beacuse meeting file contains binary data and if we write read the file not saved in path 
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.success( 
                    "✅ Meeting uploaded successfully!"
                )

                st.info(
                    "Meeting file is ready for processing."
                )

                st.write(
                    f"Saved to: `{file_path}`"
                )

            except Exception as e:

                st.error(
                    f"❌ Upload failed: {str(e)}"
                )