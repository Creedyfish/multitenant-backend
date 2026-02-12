import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_roundtrip():
    password = "s3cret"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_access_token_contains_type_and_sub():
    token = create_access_token({"sub": "johndoe"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "johndoe"
    assert payload["type"] == "access"


def test_create_refresh_token_contains_type_and_sub():
    token = create_refresh_token({"sub": "johndoe"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "johndoe"
    assert payload["type"] == "refresh"
