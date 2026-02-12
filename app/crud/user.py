from typing import Any

from app.schemas.user import UserInDB


def get_user(db: dict[str, dict[str, Any]], username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
