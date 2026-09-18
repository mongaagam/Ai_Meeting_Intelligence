<img width="1536" height="1024" alt="AI_Meeting_Intelligence" src="https://github.com/user-attachments/assets/0288687d-cbed-4d46-9143-e1ead3bb8c19" />

## 1. Authentication APIs — 4

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Create a new user account |
| POST | `/auth/login` | Authenticate user and log in |
| POST | `/auth/logout` | Log out the current user |
| GET | `/users/me` | Get current user details |

## 2. Meeting APIs — 3

| Method | Endpoint | Description |
|---|---|---|
| POST | `/meetings/upload` | Upload a meeting audio or video file |
| GET | `/meetings` | Get the list of meetings |
| GET | `/meetings/{id}` | Get details of a specific meeting |

## 3. Transcription APIs — 2

| Method | Endpoint | Description |
|---|---|---|
| POST | `/transcribe/{id}` | Start transcription for a meeting |
| GET | `/transcribe/{id}/status` | Check transcription status |

## 4. AI Analysis APIs — 2

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze/{id}` | Analyze the meeting transcript using AI |
| GET | `/results/{id}` | Get AI-generated meeting results |

## 5. Task Management APIs — 4

| Method | Endpoint | Description |
|---|---|---|
| GET | `/tasks` | Get all tasks/action items |
| POST | `/tasks` | Create a new task |
| PUT | `/tasks/{id}` | Update an existing task |
| DELETE | `/tasks/{id}` | Delete a task |

### API Summary

**Total APIs: 15**

- Authentication: 4
- Meetings: 3
- Transcription: 2
- AI Analysis: 2
- Task Management: 4
