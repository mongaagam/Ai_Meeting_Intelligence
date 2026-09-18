1. Authentication APIs — 4

POST /auth/signup
POST /auth/login
POST /auth/logout
GET /users/me

2. Meeting APIs — 3

POST /meetings/upload
GET /meetings
GET /meetings/{id}

3. Transcription APIs — 2

POST /transcribe/{id}
GET /transcribe/{id}/status

4. AI Analysis APIs — 2

POST /analyze/{id}
GET /results/{id}

5. Task Management APIs — 4

GET /tasks
POST /tasks
PUT /tasks/{id}
DELETE /tasks/{id}