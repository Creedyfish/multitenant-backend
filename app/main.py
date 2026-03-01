from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# from fastapi.security import OAuth2PasswordBearer
from app.api.v1.router import router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logger import setup_logging
from app.jobs.cleanup import scheduled_cleanup
from app.jobs.weekly_report import weekly_report

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENV,
    traces_sample_rate=1.0 if settings.ENV == "development" else 0.1,
    send_default_pii=False,
)

setup_logging()
logger = structlog.get_logger()

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
    lifespan=lifespan,
    root_path="/api/v1",
    docs_url="/docs"
    if settings.ENV == "development" or settings.ENV == "testing"
    else None,
    redoc_url="/redoc"
    if settings.ENV == "development" or settings.ENV == "testing"
    else None,
    openapi_url="/openapi.json"
    if settings.ENV == "development" or settings.ENV == "testing"
    else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
app.include_router(router)


@app.get("/health-check")
def health_check():
    return {"server": "on"}
