from fastapi import APIRouter, Depends, HTTPException

from backend.models.user import UserCreate, UserLogin

from backend.services.auth_service import (
    create_user,
    get_user_by_email,
    verify_password,
    create_access_token,
)

from backend.api.dependencies import get_current_user


# ============================================================
# ROUTER CONFIGURATION
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# SIGNUP
# POST /auth/signup
# ============================================================

@router.post("/signup")
def signup(user: UserCreate):

    existing_user = get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user_id = create_user(
        user.full_name,
        user.email,
        user.password,
    )

    if user_id is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account",
        )

    return {
        "message": "Account created successfully",
        "user_id": user_id,
    }


# ============================================================
# LOGIN
# POST /auth/login
# ============================================================

@router.post("/login")
def login(user: UserLogin):

    existing_user = get_user_by_email(user.email)

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    password_valid = verify_password(
        user.password,
        existing_user["password_hash"],
    )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        existing_user["id"],
        existing_user["email"],
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": existing_user["id"],
            "full_name": existing_user["full_name"],
            "email": existing_user["email"],
        },
    }


# ============================================================
# LOGOUT
# POST /auth/logout
# ============================================================

@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user),
):
    return {
        "message": "Logout successful. Please discard your access token."
    }


# ============================================================
# CURRENT USER
# GET /auth/users/me
# ============================================================

@router.get("/users/me")
def get_me(
    current_user: dict = Depends(get_current_user),
):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
    }
