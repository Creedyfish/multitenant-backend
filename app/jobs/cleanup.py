import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from app.db.database import SessionLocal
from app.models import PurchaseRequestStatusEnum
from app.models.purchase_request import PurchaseRequest

logger = logging.getLogger(__name__)


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
        logger.info("Deleted %d stale draft PRs", len(drafts))
    except Exception as e:
        logger.error("Draft cleanup failed  error=%s", str(e))

    finally:
        db.close()
