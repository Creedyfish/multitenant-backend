from typing import Annotated

import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# from fastapi.security import OAuth2PasswordBearer
from app.api.v1.router import router
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.db import get_db
from app.db.database import DB
from app.models import Organization, User
from app.schemas.auth import RegisterUser
from app.schemas.user import UserRead
from app.services.auth import register_organization

app = FastAPI(root_path="/api/v1")
app.include_router(router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
redis_client = redis.StrictRedis(host="0.0.0.0", port=6379, db=0, decode_responses=True)


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

    if not current_user.email == "hod":
        raise HTTPException(status_code=404, detail="user not hod")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@app.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegisterUser, db: DB):
    return register_organization(payload=payload, db=db)
