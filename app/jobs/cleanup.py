from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import and_, select

from app.db.database import SessionLocal
from app.models import PurchaseRequestStatusEnum
from app.models.purchase_request import PurchaseRequest

logger = structlog.get_logger()


def scheduled_cleanup():
    db = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        logger.info("Scheduled stale draft deletion")
        drafts = (
            db.execute(
                select(PurchaseRequest).where(
                    and_(
                        PurchaseRequest.status == PurchaseRequestStatusEnum.DRAFT,
                        PurchaseRequest.created_at < cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )
        for draft in drafts:
            db.delete(draft)
        db.commit()
        logger.info("Deleted stale draft PRs", count=len(drafts))
    except Exception as e:
        logger.error("Draft cleanup failed", error=str(e))

    finally:
        db.close()
