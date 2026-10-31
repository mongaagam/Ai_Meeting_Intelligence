from getpass import getpass

from backend.db.database import get_db
from backend.services.auth_service import hash_password

email = input("Enter your registered email: ").strip().lower()
new_password = getpass("Enter your new password: ")
confirm_password = getpass("Confirm your new password: ")

if not new_password:
    print("Password cannot be empty.")
elif new_password != confirm_password:
    print("Passwords do not match.")
else:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()

    if user is None:
        print("User not found in this database.")
    else:
        password_hash = hash_password(new_password)

        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (password_hash, email)
        )
        conn.commit()
        print("Password updated successfully.")

    conn.close()
