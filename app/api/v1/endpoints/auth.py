from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# from fastapi.security import OAuth2PasswordBearer
from app.core import verify_password
from app.db.database import DB
from app.middleware.tenant import get_tenant
from app.schemas import Token
from app.services import get_user
from app.services.auth import login, refresh

router = APIRouter()


def authenticate_user(db: DB, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


@router.post("/token")
async def login_for_access_token(
    request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB
) -> JSONResponse:
    subdomain = get_tenant(request)
    if not subdomain:
        raise HTTPException(status_code=400, detail="Tenant not identified")

    access_token, refresh_token = login(
        db, form_data.username, form_data.password, subdomain
    )

    token = Token(access_token=access_token, token_type="bearer")
    response = JSONResponse(content=token.model_dump())
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return response


@router.post("/refresh")
async def refresh_access_token(request: Request, db: DB) -> JSONResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    access_token = refresh(db, refresh_token)
    token = Token(access_token=access_token, token_type="bearer")
    return JSONResponse(content=token.model_dump())
