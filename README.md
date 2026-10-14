# AI Meeting Intelligence & Action Tracking

An AI-powered meeting intelligence system that converts recorded meeting audio and video into structured meeting information. It helps users review speaker-aware transcripts and extract meeting summaries, key topics, decisions, action items, and insights.

## Overview

The application combines a Streamlit user interface with Python backend services, SQLite storage, speech processing, speaker diarization, and LLM-based meeting analysis.

## Features

### User Authentication
- User registration and login.
- User-specific meeting dashboard and meeting records.

### Meeting Upload and Processing
- Upload audio and video meeting recordings.
- Extract audio from video using FFmpeg.
- Store uploaded meeting recordings in the project data directory.
- Save meeting metadata in SQLite.

### Transcription and Speaker Diarization
- Generate transcripts using Faster Whisper.
- Use AssemblyAI for speaker labels and speaker-related timestamps.
- Display transcript segments with speaker labels.
- Allow manual assignment of names to anonymous speaker labels.
- Update speaker names in the transcript and associated task information where supported.
- Play the full meeting recording and relevant segment audio where available.

> **Speaker identity note:** Diarization identifies different voices as speaker labels; it does not by itself know a person's real-world name. Names must be assigned manually or matched using a reliable participant metadata source.

### AI Meeting Analysis

The transcript is analyzed using Groq with the `openai/gpt-oss-20b` model to generate:

- Meeting summary
- Key topics
- Decisions
- Action items
- Meeting insights

The analysis prompt is intended to use the transcript as its source and avoid inventing missing assignees or deadlines.

### Dashboard and Meeting Details
- Display the logged-in user's meetings and meeting count.
- Open an individual meeting's details.
- View the meeting filename and upload timestamp.
- Review the transcript, summary, key topics, decisions, action items, and insights when available.

### Data Persistence
- SQLite stores application data such as user accounts and meeting metadata.
- Meeting recordings are stored separately in the uploads directory.
- The database schema and stored analysis fields depend on the current implementation.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Backend and services | Python, FastAPI |
| Database | SQLite |
| Speech-to-text | Faster Whisper |
| Speaker diarization | AssemblyAI |
| LLM analysis | Groq API (`openai/gpt-oss-20b`) |
| Audio/video extraction | FFmpeg |
| Data handling | Pandas |
| Configuration | python-dotenv |
| Version control | Git and GitHub |

## Processing Workflow

1. The user signs up or logs in.
2. The user uploads a meeting recording.
3. The application stores the file and meeting metadata.
4. Audio is prepared for speech processing when needed.
5. Faster Whisper generates transcript text.
6. AssemblyAI provides speaker labels and timing information.
7. Speaker names can be assigned manually where required.
8. The transcript is sent to Groq for meeting analysis.
9. The application displays the available transcript and AI-generated results.
10. Meeting metadata and supported results are persisted in SQLite.

## Project Structure

The structure below is based on the project folders and filenames visible in the current VS Code screenshots. Some folders may contain additional files that are not visible in the screenshots.

```text
AI_MEETING_INTELLIGENCE/
├── backend/
│   ├── api/
│   │   └── auth.py
│   ├── db/
│   │   ├── database.py
│   │   └── users.db
│   ├── models/
│   │   └── user.py
│   ├── services/
│   │   ├── ai_analysis.py
│   │   └── auth_service.py
│   └── main.py
├── data/
│   ├── outputs/
│   └── uploads/
├── docs/
│   └── API_ENDPOINTS.md
├── frontend/
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── login.py
│   │   ├── meeting_details.py
│   │   ├── meetings.py
│   │   ├── signup.py
│   │   ├── task.py
│   │   └── upload.py
│   └── app.py
├── mockups/
│   └── Mockup.html
├── scripts/
├── tests/
├── .env
├── .gitignore
├── requirements.txt
└── README.md