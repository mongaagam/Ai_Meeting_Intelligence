# Environment variable read krne ke lie
import os
# password ko security hash or verfiy krne ke lie
import bcrypt
#jwt ki expiry calculate krne ke lie
from datetime import datetime, timedelta, timezone
# json web token create krne ke lie
from jose import jwt
# .env file ke variable python me load krne ke lie
from dotenv import load_dotenv
# ye tumhari sqllit connection funtion hai
from backend.db.database import get_db


load_dotenv()

# ye jwt ko sign krne ke lie secret key hai
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
# Iska kaam hai token par digital signature banana, taaki baad mein server check kar sake
# Kya ye JWT mere trusted secret key se hi banaya gaya tha
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# time expiry
JWT_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRE_MINUTES", "60")
)


# password hashing
# hash password naam ka funcrion bnao
def hash_password(password: str) -> str:
    
    password_hash = bcrypt.hashpw(
        # string password ko bytes mein convert kar raha hai
        password.encode("utf-8"),
        # Salt ek random value hoti hai jo password hashing ko aur secure banati hai
        bcrypt.gensalt()
    )

    return password_hash.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str
) -> bool:

    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


# user database function
# Database mein kisi user ko uske email address se find karne ke liye
def get_user_by_email(email: str):
# get_db() tumhari database.py se database connection deta hai
    conn = get_db()
    # cursor database ke saath SQL commands execute karne ke liye use hota hai
    cursor = conn.cursor()
    # Ab database mein SQL query execute karo
    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email.lower(),)
    )

    # SQL query se jo result mila hai, usme se pehli row nikaalo
    user = cursor.fetchone()
    # jo database ke sath connection bnaya tha uska kaam hogya tha use close krdo
    conn.close()
    return user


def create_user(
    full_name: str,
    email: str,
    password: str
):

    password_hash = hash_password(password)

    conn = get_db()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users
            (
                full_name,
                email,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                full_name,
                email.lower(),
                password_hash
            )
        )

        conn.commit()

        user_id = cursor.lastrowid

        return user_id

    except Exception:

        return None

    finally:

        conn.close()


# jwt function jo id or mail lega aur function bnayega
def create_access_token(user_id: int, email: str):
 
# token expiry
    expire = (
        datetime.now(timezone.utc)
        + timedelta(minutes=JWT_EXPIRE_MINUTES)
    )
# JWT token ke andar user ke baare mein kaunsi information rakhni hai
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }
 
# ye actual token create krta hai
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token