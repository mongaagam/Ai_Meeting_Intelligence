# database se data read/update krne ke lie

import sqlite3

# regular expression speaker labels jaise speaker A find krne ke lie

import re

# FFmpeg Command run krne ke lie

import subprocess

# temporary audio file bnane ke lie

import tempfile

# file path handle krne ke lie

from pathlib import Path

# ui bnane ke lie

import streamlit as st





st.set_page_config(

    page_title="Meeting Details",

    page_icon="🎥",

    layout="wide"

)



# St.session_state me login session store hai

if not st.session_state.get(

    "logged_in",

    False

):

    st.warning(

        "Please login first."

    )

    # page ki future exceution rok dega

    st.stop()



# dashboard se user jis meeting par click karta hai us meeting ki id session me save hoti hai

meeting_id = st.session_state.get(

    "selected_meeting_id"

)

# Iska use ye ensure karne ke liye bhi ho raha hai ki user sirf apni meeting dekh sake

user_id = st.session_state.get(

    "user_id"

)



# no meeting selected

if not meeting_id:

    st.warning(

        "No meeting selected."

    )

    st.stop()

# aur page ruk jayega

if not user_id:

    st.warning(

        "User session not found."

    )

    st.stop()



# sqlite3.connect database open karta hai

DB_PATH = Path(

    "data/users.db"

)

conn = sqlite3.connect(

    DB_PATH

)

conn.row_factory = sqlite3.Row

cursor = conn.cursor()

cursor.execute(

    """

    SELECT

        meetings.id,

        meetings.user_id,

        meetings.filename,

        meetings.file_path,

        meetings.created_at,

        meetings.status,

        ai_analysis.transcript,

        ai_analysis.summary,

        ai_analysis.key_topics,

        ai_analysis.decisions,

        ai_analysis.action_items,

        ai_analysis.insights

    FROM meetings

    LEFT JOIN ai_analysis

        ON meetings.id = ai_analysis.meeting_id

    WHERE meetings.id = ?

        AND meetings.user_id = ?

    """,

    (

        meeting_id,

        user_id

    )

)

# database se ek matching meeting record liya jaa rha hai

meeting = cursor.fetchone()

conn.close()



# if meeting not found

if not meeting:

    st.error(

        "Meeting not found."

    )

    st.stop()





st.title(

    "🎥 Meeting Details"

)

st.subheader(

    meeting["filename"]

)

st.caption(

    f"Uploaded on: "

    f"{meeting['created_at']}"

)







status = meeting["status"]

if status == "completed":

    st.success(

        "✅ Processing completed"

    )

elif status == "processing":

    st.warning(

        "⏳ Meeting is still being processed."

    )

elif status == "failed":

    st.error(

        "❌ Meeting processing failed."

    )

else:

    st.info(

        f"Meeting status: {status}"

    )

st.divider()







st.subheader("🔊 Full Meeting Audio") 

# database me jo origional file path store ha vo liya

original_file = Path(meeting["file_path"]) 

# check krta hai ki file store hai ya nhi

if original_file.exists():

    try:

        if original_file.suffix.lower() in [

            ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"

        ]:

            # direct audio player show ho jaenga

            st.audio(str(original_file))

        else:

            # For video uploads, extract the original audio track.

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:

                output_file = Path(temp_audio.name)

            result = subprocess.run(

                [

                    "ffmpeg", "-y",

                    # i mean input vedio

                    "-i", str(original_file),

                    # vedio ko ignore karo

                    "-vn",

                    # wav audio

                    "-acodec", "pcm_s16le",

                    "-ar", "16000",

                    # mono audio

                    "-ac", "1",

                    # ui me audio player aa jata hai

                    str(output_file),

                ],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True,

            )

            if result.returncode == 0 and output_file.exists():

                st.audio(str(output_file), format="audio/wav")

            else:

                st.error("Unable to extract audio from the meeting video.")

    except Exception as e:

        st.error(f"Audio playback error: {e}")

else:

    st.warning("Original meeting file is not available.")

st.divider()

st.subheader("👥 Speakers")

st.caption("Enter the real name for each speaker. The saved name will also be used in the transcript and task assignment.")

# Load speaker mappings. These keep Speaker A/B stable while allowing

# the user to assign real names such as AgamMonga or Raj.

conn = sqlite3.connect(DB_PATH)

conn.row_factory = sqlite3.Row

speaker_rows = conn.execute(

    """

    SELECT id, speaker_label, speaker_name, voice_clip_path

    FROM meeting_speakers

    WHERE meeting_id = ?

    ORDER BY id

    """,

    (meeting_id,)

).fetchall()

# Create speaker mapping rows if the processor only saved the transcript

if meeting["transcript"] and not speaker_rows:

    # transcript se speaker label nikale jaa rhe hai

    labels = re.findall(

        r"(?:^|\n)Speaker\s+([A-Za-z0-9]+):",

        meeting["transcript"]

    )

    labels = list(dict.fromkeys(labels))

    for label in labels:

        conn.execute(

            """

            INSERT OR IGNORE INTO meeting_speakers

            (meeting_id, speaker_label, speaker_name)

            VALUES (?, ?, NULL)

            """,

            (meeting_id, label)

        )

    conn.commit()

    speaker_rows = conn.execute(

        """

        SELECT id, speaker_label, speaker_name, voice_clip_path

        FROM meeting_speakers

        WHERE meeting_id = ?

        ORDER BY id

        """,

        (meeting_id,)

    ).fetchall()

conn.close()



# kisi particular speaker ne meeting mein jitni jagah bola hai un audio portion ko nikal kar ek combined audio click banana

def get_speaker_clip(speaker_label, file_path):



    if not file_path:

        return None



    original_file = Path(file_path)



    if not original_file.exists():

        return None



    conn = sqlite3.connect(DB_PATH)



    try:

        segments = conn.execute(

            """

            SELECT start_time, end_time

            FROM speaker_segments

            WHERE meeting_id = ?

              AND speaker_label = ?

            ORDER BY start_time ASC

            """,

            (

                meeting_id,

                speaker_label

            )

        ).fetchall()



    except sqlite3.Error as e:

        print(f"Speaker clip database error: {e}")

        conn.close()

        return None



    conn.close()



    if not segments:

        return None



    temp_files = []



    try:



        # Extract every segment belonging to this speaker

        for segment in segments:



            start = max(

                float(segment[0]),

                0.0

            )



            duration = max(

                float(segment[1]) - start,

                0.1

            )



            with tempfile.NamedTemporaryFile(

                suffix=".wav",

                delete=False

            ) as temp_audio:



                segment_file = Path(temp_audio.name)



            result = subprocess.run(

                [

                    "ffmpeg",

                    "-y",

                    "-ss",

                    str(start),

                    "-i",

                    str(original_file),

                    "-t",

                    str(duration),

                    "-vn",

                    "-acodec",

                    "pcm_s16le",

                    "-ar",

                    "16000",

                    "-ac",

                    "1",

                    str(segment_file)

                ],

                stdout=subprocess.PIPE,

                stderr=subprocess.PIPE,

                text=True

            )



            if result.returncode == 0 and segment_file.exists():

                temp_files.append(segment_file)



        if not temp_files:

            return None



        # If only one segment exists

        if len(temp_files) == 1:

            audio_bytes = temp_files[0].read_bytes()

            temp_files[0].unlink(missing_ok=True)

            return audio_bytes



        # Create concat file

        with tempfile.NamedTemporaryFile(

            mode="w",

            suffix=".txt",

            delete=False

        ) as concat_file:



            concat_path = Path(concat_file.name)



            for file in temp_files:

                concat_file.write(

                    f"file '{file}'\n"

                )



        # Combine all speaker segments

        with tempfile.NamedTemporaryFile(

            suffix=".wav",

            delete=False

        ) as final_audio:



            final_path = Path(final_audio.name)



        result = subprocess.run(

            [

                "ffmpeg",

                "-y",

                "-f",

                "concat",

                "-safe",

                "0",

                "-i",

                str(concat_path),

                "-c",

                "copy",

                str(final_path)

            ],

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True

        )



        if (

            result.returncode != 0

            or not final_path.exists()

        ):

            return None





        # audio byte reture hota hai

        audio_bytes = final_path.read_bytes()



        # Cleanup

        concat_path.unlink(missing_ok=True)

        final_path.unlink(missing_ok=True)



        for file in temp_files:

            file.unlink(missing_ok=True)



        return audio_bytes



    except Exception as e:



        print(

            f"Speaker clip generation failed: {e}"

        )



        return None

# =========================================================

# 1. SPEAKERS — ASSIGN NAMES FIRST

# =========================================================

if speaker_rows:

    for speaker in speaker_rows:

        speaker_id = speaker["id"]

        speaker_label = speaker["speaker_label"]

        current_name = speaker["speaker_name"] or ""

        with st.container(border=True):

            left, right = st.columns([5, 1.6])

            with left:

                st.markdown(f"### 👤 Speaker {speaker_label}")

                name_key = f"speaker_name_{meeting_id}_{speaker_id}"

                st.text_input(

                    "Name",

                    value=current_name,

                    placeholder="Type name: Agam Monga",

                    key=name_key,

                    label_visibility="collapsed"

                )

            with right:

                st.write("")

                st.write("")

                clip = None

                # Use an already-saved clip if available; otherwise create

                # a short representative clip from speaker_segments.

                clip_path = speaker["voice_clip_path"]

                if clip_path and Path(clip_path).exists():

                    try:

                        clip = Path(clip_path).read_bytes()

                    except Exception:

                        clip = None

                if clip is None:

                    clip = get_speaker_clip(

                        speaker_label,

                        meeting["file_path"]

                    )

                if clip:

                    st.audio(clip, format="audio/wav")

                else:

                    st.caption("Voice clip unavailable")

            if st.button(

                "Save",

                key=f"save_speaker_{meeting_id}_{speaker_id}"

            ):

                entered_name = st.session_state.get(name_key, "").strip()

                conn = sqlite3.connect(DB_PATH)

                # here update speaker name

                conn.execute(

                    """

                    UPDATE meeting_speakers

                    SET speaker_name = ?

                    WHERE id = ? AND meeting_id = ?

                    """,

                    (

                        entered_name if entered_name else None,

                        speaker_id,

                        meeting_id

                    )

                )

                conn.commit()

                conn.close()

                st.success(

                    f"Speaker {speaker_label} saved as "

                    f"{entered_name or 'Speaker ' + speaker_label}."

                )

                st.rerun()

else:

    st.info("No speakers detected for this meeting yet.")

# =========================================================

# 2. TRANSCRIPT — SHOW NAME + COMPLETE SPEAKER BLOCK

# =========================================================

st.divider()

st.subheader("📄 Transcript")

conn = sqlite3.connect(DB_PATH)

name_rows = conn.execute(

    """

    SELECT speaker_label, speaker_name

    FROM meeting_speakers

    WHERE meeting_id = ?

    ORDER BY id

    """,

    (meeting_id,)

).fetchall()

conn.close()

# ab isi map ka use transcript aur tasks dono meain ho rha hai

speaker_name_map = {

    label: (name.strip() if name and name.strip() else f"Speaker {label}")

    for label, name in name_rows

}

if meeting["transcript"]:



    transcript = meeting["transcript"].strip()



    # Find every speaker label, regardless of whether

    # speakers are separated by new lines or are on the same line.

    speaker_pattern = re.compile(

        r"Speaker\s+([A-Za-z0-9]+):",

        re.IGNORECASE

    )



    matches = list(

        speaker_pattern.finditer(transcript)

    )



    if matches:



        for i, match in enumerate(matches):



            speaker_label = match.group(1)



            # Text starts after current "Speaker A:"

            start = match.end()



            # Text ends where next speaker starts

            if i + 1 < len(matches):

                end = matches[i + 1].start()

            else:

                end = len(transcript)



            spoken_text = transcript[start:end].strip()



            # Remove separator characters if present

            spoken_text = re.sub(

                r"^\s*\\*\s*|\s*\\*\s*$",

                "",

                spoken_text

            ).strip()



            if not spoken_text:

                continue

            # agr humne speaker ka naam map kar dia hai to ye yha pe show hoega transcript me

            speaker_name = speaker_name_map.get(

                speaker_label,

                f"Speaker {speaker_label}"

            )



            st.markdown(

                f"### 👤 {speaker_name}"

            )



            st.markdown(


                    spoken_text

            

            


            )



    else:



        st.markdown(

                transcript

        

        )



else:



    st.info("Transcript is not available yet.")



# Ai analysis

# ============================================================
# AI ANALYSIS
# ============================================================

import ast
import json
import pandas as pd


def parse_list(value):
    """Convert stored JSON/Python list strings into a displayable list."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(value)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, SyntaxError, TypeError):
                pass
        return value
    return str(value)


st.header("🤖 AI Analysis")

st.subheader("Summary")
if meeting["summary"]:
    st.write(meeting["summary"])
else:
    st.info("Summary is not available yet.")

# Key Topics shown as bullet points
topics = parse_list(meeting["key_topics"])
st.subheader("Key Topics")
if topics:
    for topic in topics:
        st.markdown(f"- {topic}")
else:
    st.info("No key topics identified.")

st.divider()

# Action Items
st.subheader("📌 Action Items")
action_items = meeting["action_items"]

if action_items:
    try:
        action_items_data = parse_list(action_items)
        if action_items_data:
            for item in action_items_data:
                if not isinstance(item, dict):
                    continue
                assignee = str(item.get("assignee", "Not specified")).strip()
                speaker_key = re.sub(
                    r"^Speaker\s+", "", assignee, flags=re.IGNORECASE
                ).strip()
                if speaker_key in speaker_name_map:
                    item["assignee"] = speaker_name_map[speaker_key]

            action_items_df = pd.DataFrame(action_items_data)
            for column, default in (
                ("task", "Not specified"),
                ("assignee", "Not specified"),
                ("deadline", "Not specified"),
                ("status", "Pending"),
            ):
                if column not in action_items_df.columns:
                    action_items_df[column] = default

            for column, default in (
                ("assignee", "Not specified"),
                ("deadline", "Not specified"),
                ("status", "Pending"),
            ):
                action_items_df[column] = (
                    action_items_df[column].fillna(default).replace("", default)
                )

            action_items_df = action_items_df[
                ["task", "assignee", "deadline", "status"]
            ]
            action_items_df.columns = ["Task", "Assignee", "Deadline", "Status"]
            st.table(action_items_df)
        else:
            st.info("No action items identified.")
    except Exception:
        st.info("No action items identified.")
else:
    st.info("No action items available.")

st.divider()

# Meeting Insights shown as bullet points
insights = parse_list(meeting["insights"])
st.subheader("Meeting Insights")
if insights:
    for insight in insights:
        st.markdown(f"- {insight}")
else:
    st.info("No meeting insights identified.")

st.divider()

# Decisions appear directly below Meeting Insights
decisions = parse_list(meeting["decisions"])
st.subheader("Decisions")
if decisions:
    for decision in decisions:
        st.markdown(f"- {decision}")
else:
    st.info("No decisions identified.")

st.divider()
