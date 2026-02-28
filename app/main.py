import logging
from contextlib import asynccontextmanager
from typing import Annotated

import redis
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import Depends, FastAPI, HTTPException

# from fastapi.security import OAuth2PasswordBearer
from app.api.v1.router import router
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.jobs.cleanup import scheduled_cleanup
from app.jobs.weekly_report import weekly_report
from app.models import Organization, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(  # type: ignore
        weekly_report,
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="weekly_report",
        replace_existing=True,
    )
    scheduler.add_job(  # type: ignore
        scheduled_cleanup,
        CronTrigger(hour=2, minute=0),
        id="draft_cleanup",
        replace_existing=True,
    )
    scheduler.start()  # type: ignore
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()  # type: ignore
    logger.info("Scheduler stopped")


app = FastAPI(
    root_path="/api/v1",
    docs_url="/docs" if settings.ENV == "development" else None,
    redoc_url="/redoc" if settings.ENV == "development" else None,
    openapi_url="/openapi.json" if settings.ENV == "development" else None,
)
app.include_router(router)
redis_client = redis.StrictRedis(host="0.0.0.0", port=6379, db=0, decode_responses=True)


@app.get("/settings")
def get_info():
    return settings


@app.get("/orgs/{org_id}")
def get_organization(
    org_id: str, current_user: Annotated[User, Depends(get_current_active_user)], db: DB
):
    if not current_user:
        raise HTTPException(status_code=404, detail="user not")

    if not current_user.email == "hod":
        raise HTTPException(status_code=404, detail="user not hod")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
