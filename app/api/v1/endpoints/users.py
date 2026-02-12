from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/me")
async def read_users_me(current_user: Annotated[str, Depends(get_current_user)]):
    return current_user
