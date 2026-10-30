import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
)

from backend.api.dependencies import get_current_user
from backend.db.database import get_db

router = APIRouter(prefix="/meetings", tags=["Meetings"])

UPLOAD_DIR = Path("data/uploads")
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".mov",
    ".webm",
    ".mpeg",
    ".mpga",
    ".ogg",
    ".flac",
}


@router.post("/upload", status_code=201)
async def upload_meeting(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a meeting recording and save its database record."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_name
    total_size = 0

    try:
        with file_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 200 MB limit",
                    )

                output.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        conn = get_db()

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO meetings (
                    user_id,
                    filename,
                    file_path,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    current_user["id"],
                    original_name,
                    str(file_path),
                    "uploaded",
                ),
            )

            meeting_id = cursor.lastrowid
            conn.commit()

            return {
                "message": "Meeting uploaded successfully",
                "meeting": {
                    "id": meeting_id,
                    "filename": original_name,
                    "status": "uploaded",
                    "file_size_bytes": total_size,
                },
            }

        finally:
            conn.close()

    except Exception:
        # Remove the uploaded file if processing or database insertion fails.
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


@router.get("/")
def get_meetings(
    current_user: dict = Depends(get_current_user),
):
    """Return the logged-in user's meetings and total count."""

    conn = get_db()

    try:
        cursor = conn.cursor()

        # Fetch meetings before executing the count query.
        cursor.execute(
            """
            SELECT id, filename, file_path, status, created_at
            FROM meetings
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (current_user["id"],),
        )

        meetings = [dict(row) for row in cursor.fetchall()]

        # Count meetings for the same logged-in user.
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM meetings
            WHERE user_id = ?
            """,
            (current_user["id"],),
        )

        total = cursor.fetchone()["total"]

        return {
            "total": total,
            "meetings": meetings,
        }

    finally:
        conn.close()


@router.get("/count")
def get_meeting_count(
    current_user: dict = Depends(get_current_user),
):
    """Return the total number of meetings for the logged-in user."""

    conn = get_db()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM meetings
            WHERE user_id = ?
            """,
            (current_user["id"],),
        )

        return {
            "total_meetings": cursor.fetchone()["total"]
        }

    finally:
        conn.close()


@router.get("/{meeting_id}")
def get_meeting_details(
    meeting_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Return meeting details belonging to the logged-in user."""

    conn = get_db()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                m.id,
                m.filename,
                m.file_path,
                m.status,
                m.created_at,
                a.transcript,
                a.summary,
                a.key_topics,
                a.decisions,
                a.action_items,
                a.insights
            FROM meetings AS m
            LEFT JOIN ai_analysis AS a
                ON a.meeting_id = m.id
            WHERE m.id = ?
              AND m.user_id = ?
            """,
            (meeting_id, current_user["id"]),
        )

        meeting = cursor.fetchone()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found",
            )

        return {
            "meeting": dict(meeting)
        }

    finally:
        conn.close()
