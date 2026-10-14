import sqlite3
from pathlib import Path

DB_PATH = Path("data/users.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def add_column_if_missing(
    cursor,
    table_name,
    column_name,
    column_definition
):

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if column_name not in columns:

        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {column_definition}
            """
        )


def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # user

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

# meetings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT,
            status TEXT DEFAULT 'uploaded',
            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    add_column_if_missing(
        cursor,
        "meetings",
        "status",
        "TEXT DEFAULT 'uploaded'"
    )

# ai analysis

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            transcript TEXT,
            summary TEXT,
            key_topics TEXT,
            decisions TEXT,
            action_items TEXT,
            insights TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (meeting_id)
                REFERENCES meetings(id)
                ON DELETE CASCADE,

            UNIQUE(meeting_id)
        )
    """)

# meeting speaker

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meeting_speakers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            speaker_label TEXT NOT NULL,
            speaker_name TEXT,
            voice_clip_path TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (meeting_id)
                REFERENCES meetings(id)
                ON DELETE CASCADE,

            UNIQUE(
                meeting_id,
                speaker_label
            )
        )
    """)


    # speaker segements

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS speaker_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            speaker_label TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            text TEXT,

            FOREIGN KEY (meeting_id)
                REFERENCES meetings(id)
                ON DELETE CASCADE
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            assignee_name TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'Pending',

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (meeting_id)
                REFERENCES meetings(id)
                ON DELETE CASCADE
        )
    """)


    add_column_if_missing(
        cursor,
        "tasks",
        "assignee_name",
        "TEXT"
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":

    init_db()

    print(
        "Database initialized successfully."
    )