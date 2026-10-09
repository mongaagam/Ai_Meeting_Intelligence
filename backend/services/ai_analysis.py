import os
import time
import subprocess
import sqlite3
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from faster_whisper import WhisperModel
import assemblyai as aai
load_dotenv()
groq_api_key = os.getenv("Api_Key")
assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not groq_api_key:
    raise ValueError("Groq API key not found in .env")
if not assemblyai_api_key:
    raise ValueError("AssemblyAI API key not found in .env")
client = Groq(api_key=groq_api_key)
aai.settings.api_key = assemblyai_api_key
SPEAKERS_EXPECTED = None
MIN_SPEAKERS = 2
MAX_SPEAKERS = 4
DEBUG_PRINT_UTTERANCES = True
DB_PATH = Path("data/users.db")
def update_meeting_status(meeting_id, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        UPDATE meetings
        SET status = ?
        WHERE id = ?
        """,
        (status, meeting_id)
    )
    conn.commit()
    conn.close()
def _convert_to_db_value(value):
    """Convert Groq list/dict values into SQLite-safe TEXT."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
def save_analysis_to_db(
    meeting_id, transcript, summary, key_topics,
    decisions, action_items, insights
):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO ai_analysis (
            meeting_id, transcript, summary, key_topics,
            decisions, action_items, insights
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(meeting_id)
        DO UPDATE SET
            transcript = excluded.transcript,
            summary = excluded.summary,
            key_topics = excluded.key_topics,
            decisions = excluded.decisions,
            action_items = excluded.action_items,
            insights = excluded.insights
        """,
        (
            meeting_id,
            _convert_to_db_value(transcript),
            _convert_to_db_value(summary),
            _convert_to_db_value(key_topics),
            _convert_to_db_value(decisions),
            _convert_to_db_value(action_items),
            _convert_to_db_value(insights)
        )
    )
    conn.commit()
    conn.close()
def build_assemblyai_config():
    """Create AssemblyAI config with a speaker-count hint."""
    if SPEAKERS_EXPECTED:
        return aai.TranscriptionConfig(
            speaker_labels=True,
            speakers_expected=SPEAKERS_EXPECTED
        )
    try:
        return aai.TranscriptionConfig(
            speaker_labels=True,
            speaker_options=aai.SpeakerOptions(
                min_speakers=MIN_SPEAKERS,
                max_speakers=MAX_SPEAKERS
            )
        )
    except (AttributeError, TypeError):
        print(
            "Warning: SpeakerOptions not supported by installed "
            "assemblyai SDK. Falling back to default diarization."
        )
        return aai.TranscriptionConfig(speaker_labels=True)
def find_speaker(start, end, speaker_segments):
    """
    Assign a Whisper word to the AssemblyAI speaker segment.
    The midpoint of each Whisper word is used instead of total overlap.
    This prevents a word near a speaker boundary from being assigned
    to the previous speaker just because the word overlaps two intervals.
    """
    if not speaker_segments:
        return "Unknown"
    mid = (start + end) / 2
    for seg in speaker_segments:
        if seg["start"] <= mid <= seg["end"]:
            return seg["speaker"]
    nearest = min(
        speaker_segments,
        key=lambda s: min(
            abs(mid - s["start"]),
            abs(mid - s["end"])
        )
    )
    return nearest["speaker"]
def process_meeting(meeting_id, audio_file):
    print("\n")
    print("=" * 60)
    print("STARTING MEETING PROCESSING")
    print("=" * 60)
    update_meeting_status(meeting_id, "processing")
    try:
        if not os.path.exists(audio_file):
            raise FileNotFoundError(
                f"Meeting file not found: {audio_file}"
            )
        print(f"\nFile: {audio_file}")
        model_size = "medium"
        print("\nLoading Faster-Whisper model...")
        whisper_start_time = time.time()
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=8,
            num_workers=1
        )
        print("Faster-Whisper model loaded.")
        print("\nTranscribing meeting with Faster-Whisper...")
        segments, info = model.transcribe(
            audio_file,
            task="translate",
            beam_size=3,
            vad_filter=True,
            condition_on_previous_text=False,
            word_timestamps=True
        )
        whisper_words = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    token = w.word.strip()
                    if token:
                        whisper_words.append({
                            "start": w.start,
                            "end": w.end,
                            "text": token
                        })
            else:
                text = segment.text.strip()
                if text:
                    whisper_words.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": text
                    })
        if not whisper_words:
            raise ValueError("Faster-Whisper transcript is empty.")
        whisper_elapsed = time.time() - whisper_start_time
        print(
            f"Faster-Whisper transcription completed "
            f"in {whisper_elapsed / 60:.2f} minutes."
        )
        print(f"Total Whisper words: {len(whisper_words)}")
        print("\nPreparing audio for AssemblyAI...")
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        base_name = os.path.splitext(
            os.path.basename(audio_file)
        )[0]
        assembly_audio_file = upload_dir / f"{base_name}_diar.mp3"
        if not assembly_audio_file.exists():
            print("\nExtracting audio from meeting video...")
            ffmpeg_start_time = time.time()
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i", audio_file,
                        "-vn",
                        "-ac", "1",
                        "-ar", "16000",
                        "-b:a", "128k",
                        str(assembly_audio_file)
                    ],
                    check=True
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "FFmpeg was not found. "
                    "Please install FFmpeg and add it to PATH."
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"FFmpeg audio extraction failed: {e}"
                )
            ffmpeg_elapsed = time.time() - ffmpeg_start_time
            print(
                f"Audio extraction completed "
                f"in {ffmpeg_elapsed:.2f} seconds."
            )
        else:
            print("\nCompressed audio already exists.")
            print("Skipping FFmpeg conversion.")
        print("\nRunning AssemblyAI speaker diarization...")
        assembly_start_time = time.time()
        config = build_assemblyai_config()
        transcriber = aai.Transcriber(config=config)
        max_retries = 3
        assembly_transcript = None
        for attempt in range(1, max_retries + 1):
            try:
                print(
                    f"\nUploading audio to AssemblyAI "
                    f"(attempt {attempt}/{max_retries})..."
                )
                assembly_transcript = transcriber.transcribe(
                    str(assembly_audio_file)
                )
                break
            except Exception as e:
                print(f"AssemblyAI attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    raise RuntimeError(
                        "AssemblyAI upload/transcription "
                        "failed after multiple attempts."
                    )
                time.sleep(5)
        if assembly_transcript is None:
            raise RuntimeError("AssemblyAI returned no transcript.")
        if assembly_transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(
                f"AssemblyAI failed: {assembly_transcript.error}"
            )
        assembly_elapsed = time.time() - assembly_start_time
        print(
            f"\nAssemblyAI diarization completed "
            f"in {assembly_elapsed / 60:.2f} minutes."
        )
        if not assembly_transcript.utterances:
            raise ValueError(
                "AssemblyAI did not return speaker utterances."
            )
        speaker_segments = []
        for utterance in assembly_transcript.utterances:
            speaker_segments.append({
                "start": utterance.start / 1000,
                "end": utterance.end / 1000,
                "speaker": utterance.speaker
            })
        print(f"Speaker segments found: {len(speaker_segments)}")
        print("\n--- SPEAKER BOUNDARIES ---")
        for seg in speaker_segments:
            print(
                f"[{seg['start']:7.2f}s - {seg['end']:7.2f}s] "
                f"Speaker {seg['speaker']}"
            )
        print("--- END SPEAKER BOUNDARIES ---\n")
        if DEBUG_PRINT_UTTERANCES:
            print("\n--- RAW ASSEMBLYAI UTTERANCES ---")
            for utterance in assembly_transcript.utterances:
                print(
                    f"[{utterance.start / 1000:7.2f}s - "
                    f"{utterance.end / 1000:7.2f}s] "
                    f"Speaker {utterance.speaker}: "
                    f"{utterance.text[:80]}"
                )
            print("--- END RAW UTTERANCES ---\n")
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                DELETE FROM speaker_segments
                WHERE meeting_id = ?
                """,
                (meeting_id,)
            )
            for segment in speaker_segments:
                conn.execute(
                    """
                    INSERT INTO speaker_segments
                    (
                        meeting_id,
                        speaker_label,
                        start_time,
                        end_time
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        segment["speaker"],
                        segment["start"],
                        segment["end"]
                    )
                )
            conn.commit()
        finally:
            conn.close()
        print(
            f"Saved {len(speaker_segments)} "
            f"speaker segments to database."
        )
        labeled_words = []
        for w in whisper_words:
            labeled_words.append({
                "speaker": find_speaker(
                    w["start"], w["end"], speaker_segments
                ),
                "text": w["text"]
            })
        merged_transcript = []
        for item in labeled_words:
            if (
                merged_transcript
                and merged_transcript[-1]["speaker"] == item["speaker"]
            ):
                merged_transcript[-1]["text"] += " " + item["text"]
            else:
                merged_transcript.append({
                    "speaker": item["speaker"],
                    "text": item["text"]
                })
        transcript_parts = []
        for item in merged_transcript:
            transcript_parts.append(
                f"Speaker {item['speaker']}: {item['text']}"
            )
        transcript = "\n\n".join(transcript_parts)
        if not transcript.strip():
            raise ValueError("Speaker transcript is empty.")
        print("\n")
        print("=" * 60)
        print("FINAL SPEAKER TRANSCRIPT")
        print("=" * 60)
        print()
        print(transcript)
        print()
        print("=" * 60)
        print("\nAI analysis in progress...")
        prompt = f"""
You are an AI meeting analysis assistant.
Analyze the following meeting transcript and provide a structured meeting analysis.
Return ONLY valid JSON.
Do not return Markdown.
Do not return ```json.
Do not add any text before or after the JSON.
Return the JSON in exactly this format:
{{
    "summary": "...",
    "key_topics": [
        "- Topic 1",
        "- Topic 2",
        "- Topic 3"
    ],
    "decisions": [
        "- Decision 1",
        "- Decision 2"
    ],
    "action_items": [
        {{
            "task": "Task description",
            "assignee": "Assignee name or Not specified",
            "deadline": "Deadline or Not specified"
        }}
    ],
    "insights": [
        "- Insight 1",
        "- Insight 2",
        "- Insight 3"
    ]
}}
IMPORTANT RULES:
1. SUMMARY
- Provide a concise summary of the meeting.
- Use ONLY information explicitly mentioned in the transcript.
- Do not invent or assume information.
- Return the summary as a normal paragraph.
- Do NOT add bullet points to the summary.
2. KEY TOPICS
- List the main topics discussed in the meeting.
- Only include topics explicitly mentioned in the transcript.
- Do not add information from outside the transcript.
- Each topic MUST start with "- ".
- Keep each topic concise.
3. DECISIONS
- List only decisions that were explicitly made during the meeting.
- Do not treat a discussion, suggestion, question, or possibility as a decision.
- Each decision MUST start with "- ".
- If no decisions are explicitly mentioned, return:
  [
      "- No decisions identified"
  ]
4. ACTION ITEMS
- Extract all tasks or actions that need to be completed based on the transcript.
- Each action item MUST contain:
    - task
    - assignee
    - deadline
- If the assignee is explicitly mentioned, use that name.
- If the assignee is NOT explicitly mentioned, write:
  "Not specified"
- If the deadline is explicitly mentioned, use the exact deadline mentioned.
- If the deadline is NOT explicitly mentioned, write:
  "Not specified"
- NEVER guess or infer an assignee.
- NEVER guess or infer a deadline.
- NEVER use today's date as a deadline unless it is explicitly mentioned.
- NEVER calculate a deadline.
- NEVER assign a task to a speaker just because that speaker mentioned the task.
- Only create an action item when the transcript indicates that something needs to be done.
- If there are no action items, return:
  [
      {{
          "task": "No action items identified",
          "assignee": "Not specified",
          "deadline": "Not specified"
      }}
  ]
5. MEETING INSIGHTS
- Provide useful observations based ONLY on the transcript.
- Do not introduce external knowledge.
- Do not invent information.
- Each insight MUST start with "- ".
- Keep each insight concise.
GENERAL RULES:
- Use ONLY information explicitly present in the transcript.
- Never hallucinate.
- Never guess names.
- Never guess roles.
- Never guess assignees.
- Never guess deadlines.
- Preserve the original meaning of the transcript.
- Keep the analysis factual and concise.
- Make sure the output is valid JSON.
- Make sure every opening JSON bracket has a matching closing bracket.
Meeting Transcript:
{transcript}
"""
        ai_start_time = time.time()
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=1500,
                reasoning_effort="low"
            )
        except Exception as e:
            raise RuntimeError(f"Groq AI analysis failed: {e}")
        result = response.choices[0].message.content
        ai_elapsed = time.time() - ai_start_time
        if not result:
            raise ValueError("Groq returned an empty AI analysis.")
        result = result.strip()
        result = re.sub(
            r"^```json\s*", "", result, flags=re.IGNORECASE
        )
        result = re.sub(r"^```\s*", "", result)
        result = re.sub(r"\s*```$", "", result)
        try:
            analysis = json.loads(result)
        except json.JSONDecodeError:
            print("Warning: Groq did not return valid JSON.")
            analysis = {
                "summary": result,
                "key_topics": "Not available",
                "decisions": "No decisions identified",
                "action_items": "No action items identified",
                "insights": "Not available"
            }
        summary = analysis.get("summary", "Summary not available.")
        key_topics = analysis.get("key_topics", "No key topics identified.")
        decisions = analysis.get("decisions", "No decisions identified")
        action_items = analysis.get(
            "action_items", "No action items identified"
        )
        insights = analysis.get("insights", "No insights available.")
        save_analysis_to_db(
            meeting_id=meeting_id,
            transcript=transcript,
            summary=summary,
            key_topics=key_topics,
            decisions=decisions,
            action_items=action_items,
            insights=insights
        )
        update_meeting_status(meeting_id, "completed")
        print(f"AI analysis completed in {ai_elapsed:.2f} seconds.")
        print("=" * 60)
        return {
            "success": True,
            "transcript": transcript,
            "summary": summary,
            "key_topics": key_topics,
            "decisions": decisions,
            "action_items": action_items,
            "insights": insights
        }
    except Exception as e:
        update_meeting_status(meeting_id, "failed")
        print(f"\nMeeting processing failed: {e}")
        raise
