from uuid import UUID

from sqlalchemy import select

from app.db.database import DB
from app.models.user import RefreshToken


def get_refresh_token(db: DB, user_id: UUID, refresh_token: str) -> RefreshToken | None:
    return db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.token == refresh_token
        )
    ).scalar_one_or_none()
