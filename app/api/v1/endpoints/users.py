from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_active_user
from app.models import User
from app.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user
