# AI Meeting Intelligence & Action Tracking

An AI-powered meeting intelligence system that converts meeting audio or video recordings into structured and useful information such as meeting summaries, decisions, action items, assignees, deadlines, and task status.

The main goal of this project is to reduce the manual effort required to review meetings and track tasks discussed during them.

---

# 1. Project Overview

Meetings often contain important discussions, decisions, and tasks, but manually reviewing recordings and identifying action items can take a lot of time.

This project automates this process.

The user uploads a meeting audio or video file through the Streamlit application. The system processes the recording, converts speech into text using Faster-Whisper, and then uses an LLM to understand the transcript and extract important meeting information.

The generated information is stored in a database and displayed through a Streamlit dashboard.

The system can identify:

- Meeting summary
- Important decisions
- Action items
- Task assignees
- Deadlines
- Task status
- Meeting history

---

# 2. Objectives

The main objectives of the project are:

- Convert meeting recordings into text automatically.
- Generate a useful meeting summary.
- Identify important decisions made during the meeting.
- Extract action items from the conversation.
- Identify the person responsible for each task.
- Extract deadlines when mentioned.
- Track the status of tasks.
- Store meeting information for future reference.
- Provide a dashboard to view meeting information.
- Allow users to find tasks assigned to a particular person.

---

# 3. Key Features

## 3.1 Meeting File Upload

Users can upload meeting audio or video recordings through the Streamlit interface.

Supported formats can include:

- MP3
- WAV
- M4A
- MP4
- MOV

The uploaded file is validated before processing.

```text
User
  ↓
Upload Meeting
  ↓
File Validation
  ↓
Processing Pipeline
```

---

## 3.2 Audio Extraction

If the uploaded file is a video, FFmpeg is used to extract the audio from the video file.

```text
meeting.mp4
     ↓
   FFmpeg
     ↓
meeting.wav
```

The extracted audio is then passed to Faster-Whisper for transcription.

---

## 3.3 Speech-to-Text

Faster-Whisper is used to convert the meeting audio into text.

```text
Audio
  ↓
Faster-Whisper
  ↓
Transcript
```

The generated transcript represents what was spoken during the meeting.

For example:

```text
Audio:
"Agam will complete the Whisper testing by Friday."

        ↓

Transcript:
"Agam will complete the Whisper testing by Friday."
```

The main responsibility of Faster-Whisper is:

```text
Speech → Text
```

---

## 3.4 AI Meeting Analysis

The transcript is passed to an LLM for further analysis.

The LLM understands the conversation and extracts useful meeting information such as:

- Summary
- Decisions
- Action items
- Assignees
- Deadlines
- Task status

Faster-Whisper answers:

```text
What was said?
```

The LLM answers:

```text
What does it mean?
```

---

## 3.5 Action Item Extraction

The system identifies tasks discussed during the meeting.

For example:

```text
"Agam will complete the Whisper testing by Friday."
```

The system can convert this into:

```text
Task: Complete Whisper testing
Assignee: Agam
Deadline: Friday
Status: In Progress
```

---

## 3.6 Task Search by Person

Users can search for a person and view the tasks assigned to them.

Example:

```text
Search: Agam
```

Result:

```text
Task: Complete Whisper testing
Meeting: Project Discussion
Deadline: Friday
Status: In Progress
```

This makes it easier for users to quickly find their responsibilities across different meetings.

---

## 3.7 Meeting History

Previously processed meetings can be stored and accessed later.

Users can view:

- Meeting name
- Meeting date
- Transcript
- Summary
- Decisions
- Action items

---

## 3.8 Dashboard

The Streamlit dashboard provides an overview of the meeting data.

The dashboard can display:

- Total meetings
- Total action items
- Pending tasks
- Completed tasks
- Meeting summaries
- Decisions
- Action items

---

# 4. System Architecture

The application is divided into different components where each component performs a specific task.

## Architecture Diagram

```text
                         USER
                           |
                           v
                    +-------------+
                    |  Streamlit  |
                    |     UI      |
                    +------+------+
                           |
                           v
                  +-----------------+
                  | File Upload &   |
                  |   Validation    |
                  +--------+--------+
                           |
                           v
                      +---------+
                      | FFmpeg  |
                      +----+----+
                           |
                           v
                 +-------------------+
                 |  Faster-Whisper   |
                 |   Speech-to-Text  |
                 +---------+---------+
                           |
                           v
                    +-------------+
                    | Transcript  |
                    +------+------+
                           |
                           v
                       +-------+
                       |  LLM  |
                       +---+---+
                           |
                           v
              +--------------------------+
              | Meeting Analysis         |
              |                          |
              | - Summary                |
              | - Decisions              |
              | - Action Items           |
              | - Assignees              |
              | - Deadlines              |
              | - Task Status            |
              +------------+-------------+
                           |
                           v
                    +-------------+
                    |  Database   |
                    +------+------+
                           |
                           v
                    +-------------+
                    |  Streamlit  |
                    |  Dashboard  |
                    +-------------+
```

---

# 5. End-to-End Processing Flow

The complete meeting-processing workflow is:

```text
Meeting Audio/Video
        ↓
Streamlit File Upload
        ↓
File Validation
        ↓
FFmpeg
        ↓
Audio File
        ↓
Faster-Whisper
        ↓
Meeting Transcript
        ↓
LLM Analysis
        ↓
Structured Meeting Information
        ↓
Database
        ↓
Streamlit Dashboard
```

---

# 6. Component Explanation

## 6.1 Streamlit

Streamlit is used as the main user interface of the application.

It handles:

- Login
- File upload
- Processing status
- Meeting summary
- Decisions
- Action items
- Meeting history
- Task search
- Dashboard

The basic interaction is:

```text
User
  ↓
Streamlit
  ↓
Python Application
```

---

## 6.2 Python

Python acts as the main application and integration layer.

It connects the different components of the system.

Python is responsible for:

- Handling uploaded files
- File validation
- Calling FFmpeg
- Running Faster-Whisper
- Sending transcripts to the LLM
- Processing LLM responses
- Storing results
- Retrieving database information
- Passing data to Streamlit

---

## 6.3 FFmpeg

FFmpeg is used for media processing.

Its main responsibilities are:

- Extracting audio from video
- Converting audio formats
- Preparing audio for transcription

FFmpeg does not understand the content of the meeting.

Its role is:

```text
Audio / Video
      ↓
Audio Preparation
```

---

## 6.4 Faster-Whisper

Faster-Whisper is responsible for speech-to-text conversion.

Its main responsibility is:

```text
Speech → Text
```

For example:

```text
Audio:
"Agam will complete the testing by Friday."

        ↓

Transcript:
"Agam will complete the testing by Friday."
```

Faster-Whisper does not perform meeting analysis.

---

## 6.5 LLM

The LLM is responsible for understanding the transcript.

The transcript is passed to the LLM, which analyzes the conversation and extracts useful information.

The LLM can identify:

- Summary
- Decisions
- Action items
- Assignees
- Deadlines
- Task status

For example:

```text
Agam: I will complete the Whisper testing by Friday.
```

The LLM can generate:

```text
Task: Complete Whisper testing
Assignee: Agam
Deadline: Friday
Status: In Progress
```

---

## 6.6 Database

The database stores the generated meeting information.

It can store:

- User information
- Meeting details
- Meeting date
- Transcript
- Summary
- Decisions
- Action items
- Assignees
- Deadlines
- Task status

SQLite can be used during initial development.

A production version can later use PostgreSQL or another suitable database.

---

# 7. Structured LLM Output

The LLM output should be structured so that it can easily be stored and displayed.

A JSON-based format can be used.

Example:

```json
{
  "summary": "The team discussed the meeting intelligence project.",
  "decisions": [
    "Use Faster-Whisper for speech-to-text."
  ],
  "action_items": [
    {
      "task": "Complete Whisper testing",
      "assignee": "Agam",
      "deadline": "Friday",
      "status": "In Progress"
    }
  ]
}
```

Structured output makes it easier to:

- Store data
- Search tasks
- Display results
- Track task status
- Retrieve meeting information
- Integrate with other systems

---

# 8. Data Flow

The complete data flow is:

```text
                  MEETING FILE
                       |
                       v
                   STREAMLIT
                       |
                       v
                FILE VALIDATION
                       |
                       v
                    FFMPEG
                       |
                       v
                   AUDIO FILE
                       |
                       v
                FASTER-WHISPER
                       |
                       v
                  TRANSCRIPT
                       |
                       v
                      LLM
                       |
                       v
              STRUCTURED RESULTS
                       |
              +--------+--------+
              |        |        |
              v        v        v
           Summary  Decisions  Action Items
                                  |
                                  v
                               DATABASE
                                  |
                                  v
                               STREAMLIT
                                  |
                                  v
                               DASHBOARD
```

---

# 9. Authentication

The application can include authentication so that only authorized users can access the system.

The basic login flow is:

```text
User
 ↓
Login
 ↓
Authentication
 ↓
Dashboard
```

Authentication can be used to maintain user-specific meeting and task information.

# 10. Meeting History

The application can maintain previously processed meetings.

Example:

```text
Meeting History
       ↓
Select Meeting
       ↓
Meeting Details
       ↓
Summary + Decisions + Action Items
```

This allows users to access previous meeting information without processing the same recording again.

---

