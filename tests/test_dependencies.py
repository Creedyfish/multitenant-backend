import pytest
from fastapi import HTTPException

from app.core.dependencies import get_current_active_user, get_current_user
from app.core.security import create_access_token
from app.schemas.user import User


@pytest.mark.anyio
async def test_get_current_user_valid_token():
    token = create_access_token({"sub": "johndoe"})
    user = await get_current_user(token)
    assert user.username == "johndoe"


@pytest.mark.anyio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("invalid.token.value")
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_get_current_active_user_inactive():
    user = User(username="inactive", disabled=True)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(user)
    assert exc_info.value.status_code == 400
