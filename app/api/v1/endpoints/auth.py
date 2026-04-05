from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

# from fastapi.security import OAuth2PasswordBearer
from app.core import verify_password
from app.core.limiter import limiter
from app.db.database import DB
from app.middleware.tenant import get_tenant
from app.schemas import Token
from app.services.auth import login, refresh, revoke_refresh_token
from app.services.user import UserService

router = APIRouter()
logger = structlog.get_logger()


def authenticate_user(db: DB, username: str, password: str):
    user = UserService(db).get_by_email(username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


@router.post("/token")
@limiter.limit("5/minute")  # type: ignore
async def login_for_access_token(
    request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB
) -> JSONResponse:
    subdomain = get_tenant(request)
    if not subdomain:
        raise HTTPException(status_code=400, detail="Tenant not identified")

    try:
        access_token, refresh_token = login(
            db, form_data.username, form_data.password, subdomain
        )
        logger.info("Login successful", email=form_data.username, subdomain=subdomain)
    except HTTPException as e:
        logger.warning(
            "Login failed",
            email=form_data.username,
            subdomain=subdomain,
            reason=e.detail,
        )
        raise

    token = Token(access_token=access_token, token_type="bearer")
    response = JSONResponse(content=token.model_dump())
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return response


@router.post("/refresh")
async def refresh_access_token(request: Request, db: DB) -> JSONResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("Refresh attempted with no token")
        raise HTTPException(status_code=401, detail="No refresh token")

    # Now unpacks both tokens
    access_token, new_refresh_token = refresh(db, refresh_token)
    logger.info("Token refreshed successfully")

    token = Token(access_token=access_token, token_type="bearer")
    response = JSONResponse(content=token.model_dump())
    # Set the new rotated refresh token as the cookie
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True)
    return response


@router.post("/logout")
async def logout(request: Request, db: DB) -> JSONResponse:
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        try:
            revoke_refresh_token(db, refresh_token)
        except Exception:
            pass  # Cookie still gets cleared regardless

    logger.info("User logged out")
    response = JSONResponse(
        content={"success": True, "message": "Logged out successfully"}
    )
    response.delete_cookie(key="refresh_token", httponly=True)
    return response
