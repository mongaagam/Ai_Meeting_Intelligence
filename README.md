# AI Meeting Intelligence & Action Tracking

An AI-powered meeting intelligence system that converts meeting audio/video recordings into structured meeting information such as summaries, decisions, action items, assignees, deadlines, and task status.

## Features

- Upload meeting audio/video files
- Audio extraction using FFmpeg
- Speech-to-text using Faster-Whisper
- AI-based meeting analysis using LLM
- Automatic summary generation
- Decision extraction
- Action item extraction
- Assignee and deadline identification
- Task status tracking
- Meeting history
- Find tasks by person
- Streamlit-based dashboard

## Project Structure

```text
AI-Meeting-Intelligence/
│
├── backend/                 # Main application and processing logic
│
├── data/                    # Meeting files and generated data
│   ├── uploads/             # Uploaded audio/video files
│   ├── audio/               # Extracted or converted audio files
│   ├── transcripts/         # Generated transcripts
│   └── results/             # LLM-generated meeting results
│
├── docs/                    # Project documentation and diagrams
│
├── frontend/                # Streamlit UI related code
│
├── mockups/                 # UI designs and mockups
│   └── Mockup.html          # Meeting application UI mockup
│
├── scripts/                 # Helper and utility scripts
│
├── tests/                   # Testing files
│
├── .env                     # API keys and environment configuration
│                             # Do not push this file to GitHub
│
├── .gitignore               # Files and folders ignored by Git
│
├── Architecture.md          # Detailed system architecture
│
└── README.md                # Main project documentation
```
