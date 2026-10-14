from fastapi import APIRouter, HTTPException

from backend.models.user import (
    UserCreate,
    UserLogin
)

from backend.services.auth_service import (
    create_user,
    get_user_by_email,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# signup

@router.post("/signup")
def signup(user: UserCreate):

    existing_user = get_user_by_email(
        user.email
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_id = create_user(
        user.full_name,
        user.email,
        user.password
    )

    if user_id is None:

        raise HTTPException(
            status_code=400,
            detail="Unable to create account"
        )

    return {
        "message": "Account created successfully",
        "user_id": user_id
    }


# login
@router.post("/login")
def login(user: UserLogin):

    existing_user = get_user_by_email(
        user.email
    )

    if not existing_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_valid = verify_password(
        user.password,
        existing_user["password_hash"]
    )

    if not password_valid:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Generate JWT
    access_token = create_access_token(
        existing_user["id"],
        existing_user["email"]
    )

    return {
        "message": "Login successful",

        "access_token": access_token,

        "token_type": "bearer",

        "user": {
            "id": existing_user["id"],
            "full_name": existing_user["full_name"],
            "email": existing_user["email"]
        }
    }