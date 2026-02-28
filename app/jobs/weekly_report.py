import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select

from app.db.database import SessionLocal
from app.models import PurchaseRequestStatusEnum
from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.product import Product
from app.models.purchase_request import PurchaseRequest
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.services.email import send_weekly_report
from app.services.stock_movement import StockService

logger = logging.getLogger(__name__)


def weekly_report():
    db = SessionLocal()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        orgs = db.execute(select(Organization.id, Organization.name)).all()
        for org_id, org_name in orgs:
            try:
                users = (
                    db.execute(
                        select(User.email)
                        .where(User.org_id == org_id)
                        .where(
                            or_(
                                User.role == RoleEnum.ADMIN,
                                User.role == RoleEnum.MANAGER,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                weekly_movements = db.execute(
                    select(
                        StockMovement.type,
                        func.sum(StockMovement.quantity).label("total"),
                    )
                    .where(
                        and_(
                            StockMovement.org_id == org_id,
                            StockMovement.created_at >= week_ago,
                        )
                    )
                    .group_by(StockMovement.type)
                ).all()
                totals = {row.type: row.total for row in weekly_movements}
                stock_levels = StockService(db).get_stock_levels(org_id)
                product_ids = [s.product_id for s in stock_levels]
                products = (
                    db.execute(select(Product).where(Product.id.in_(product_ids)))
                    .scalars()
                    .all()
                )
                product_map = {p.id: p for p in products}
                low_stock_products = [
                    s
                    for s in stock_levels
                    if s.current_stock < product_map[s.product_id].min_stock_level
                ]
                pending_prs = (
                    db.execute(
                        select(PurchaseRequest).where(
                            and_(
                                PurchaseRequest.org_id == org_id,
                                or_(
                                    PurchaseRequest.status
                                    == PurchaseRequestStatusEnum.SUBMITTED,
                                    PurchaseRequest.status
                                    == PurchaseRequestStatusEnum.APPROVED,
                                ),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )

                send_weekly_report(
                    recipients=list(users),
                    org_name=org_name,
                    totals=totals,
                    low_stock_products=low_stock_products,
                    pending_prs=list(pending_prs),
                )
            except Exception as e:
                logger.error(
                    "Weekly report failed  org_id=%s  error=%s", org_id, str(e)
                )
    except Exception as e:
        logger.error("Weekly report failed  error=%s", str(e))
    finally:
        db.close()
