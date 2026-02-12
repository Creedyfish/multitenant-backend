from typing import Annotated, Any

import jwt
import redis
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# from fastapi.security import OAuth2PasswordBearer
from app.api.v1.router import router
from app.core.config import settings
from app.core.dependencies import fake_users_db, get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.crud.user import get_user
from app.db.database import get_db
from app.models.organization import Organization
from app.schemas.auth import Token
from app.schemas.user import User

app = FastAPI(root_path="/api/v1")
app.include_router(router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
redis_client = redis.StrictRedis(host="0.0.0.0", port=6379, db=0, decode_responses=True)


def authenticate_user(db: dict[str, Any], username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> JSONResponse:  # Return type is Token, not Response
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "disabled": user.disabled},
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "disabled": user.disabled}
    )

    token = Token(
        access_token=access_token,
        token_type="bearer",
    )

    # Create response to set cookie
    response = JSONResponse(content=token.model_dump())
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
    )

    print(access_token)
    return response


@app.post("/refresh")
async def refresh_access_token(
    request: Request,
) -> JSONResponse:  # Return type is Token, not Response

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    print({"refresh": refresh_token})

    payload = jwt.decode(
        refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    username = payload.get("sub")
    disabled = payload.get("disabled")
    # get verify refresh token

    access_token = create_access_token(
        data={"sub": username, "disabled": disabled},
    )

    token = Token(
        access_token=access_token,
        token_type="bearer",
    )
    response = JSONResponse(content=token.model_dump())
    return response


@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


@app.get("/settings")
def get_info():
    return settings


@app.get("/orgs/{org_id}")
def get_organization(
    org_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=404, detail="user not")

    if not current_user.username == "hod":
        raise HTTPException(status_code=404, detail="user not hod")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
