import pytest
from unittest.mock import MagicMock, patch

from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
)


# Test 1: Password successfully hash hona chahiye
def test_hash_password():
    password = "TestPassword123"

    password_hash = hash_password(password)

    assert password_hash != password
    assert isinstance(password_hash, str)


# Test 2: Correct password verify hona chahiye
def test_verify_password_correct():
    password = "TestPassword123"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


# Test 3: Wrong password reject hona chahiye
def test_verify_password_wrong():
    password = "TestPassword123"
    password_hash = hash_password(password)

    assert verify_password("WrongPassword123", password_hash) is False


# Test 4: Har baar password ka hash alag hona chahiye
# bcrypt random salt use karta hai
def test_hash_password_uses_random_salt():
    password = "TestPassword123"

    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


# Test 5: JWT token create hona chahiye
@patch("backend.services.auth_service.JWT_SECRET_KEY", "test-secret-key")
def test_create_access_token():
    from jose import jwt

    token = create_access_token(1, "test@example.com")

    payload = jwt.decode(
        token,
        "test-secret-key",
        algorithms=["HS256"],
    )

    assert payload["sub"] == "1"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
