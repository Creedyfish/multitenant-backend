"""
Tests for app/jobs/weekly_report.py — weekly_report()

Strategy:
- Patches SessionLocal to use the test DB session
- Mocks send_weekly_report to avoid sending real emails (one real email test included)
- Verifies the correct data is passed to send_weekly_report per org

Run with:
    pytest tests/test_weekly_report.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import DB
from app.jobs.weekly_report import weekly_report
from app.models.enums import PurchaseRequestStatusEnum, RoleEnum, StockMovementTypeEnum
from app.models.product import Product
from app.models.purchase_request import PurchaseRequest
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from tests.conftest import make_org, make_user

# ── Helpers ────────────────────────────────────────────────────────────────────


def make_product(
    db: DB,
    org_id: uuid.UUID,
    name: str = "Widget",
    sku: str = "SKU-001",
    min_stock_level: int = 10,
):
    p = Product(org_id=org_id, sku=sku, name=name, min_stock_level=min_stock_level)
    db.add(p)
    db.flush()
    db.refresh(p)
    return p


def make_warehouse(
    db: DB, org_id: uuid.UUID, name: str = "Warehouse", location: str = "HQ"
):
    w = Warehouse(org_id=org_id, name=name, location=location)
    db.add(w)
    db.flush()
    db.refresh(w)
    return w


def add_movement(
    db: DB,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    movement_type: StockMovementTypeEnum,
    quantity: int,
    created_by: uuid.UUID,
    days_ago: int = 1,
):
    m = StockMovement(
        org_id=org_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        type=movement_type,
        quantity=quantity,
        created_by=created_by,
    )
    db.add(m)
    db.flush()
    if days_ago != 1:
        ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
        db.execute(
            text("UPDATE stock_movements SET created_at = :ts WHERE id = :id"),
            {"ts": ts, "id": m.id},
        )
        db.flush()
    return m


def make_purchase_request(
    db: DB,
    org_id: uuid.UUID,
    created_by: uuid.UUID,
    status: PurchaseRequestStatusEnum,
    request_number: str = "PR-00001",
):
    pr = PurchaseRequest(
        org_id=org_id,
        request_number=request_number,
        status=status,
        created_by=created_by,
    )
    db.add(pr)
    db.flush()
    db.refresh(pr)
    return pr


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_weekly_report_sends_real_email(db: Session):
    """
    REAL EMAIL TEST — check inbox at ielbanbuenawork@gmail.com.

    Sets up one org with an admin, some stock movements, a low stock product,
    and a pending PR, then fires the real weekly_report job.
    """
    org = make_org(db, name="Weekly Report Org", subdomain="weekly-real")
    admin = make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="Real Report Widget", sku="SKU-REAL-WR", min_stock_level=20
    )
    warehouse = make_warehouse(db, org.id, name="Real Warehouse", location="Real HQ")

    # Stock in 5 → below min of 20
    add_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.IN, 5, admin.id
    )
    make_purchase_request(
        db, org.id, admin.id, PurchaseRequestStatusEnum.SUBMITTED, "PR-00001"
    )
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        weekly_report()

    # Check ielbanbuenawork@gmail.com for the weekly report email.


def test_send_weekly_report_called_once_per_org(db: Session):
    """
    weekly_report should call send_weekly_report exactly once per org.
    With 2 orgs in DB, it should be called twice.
    """
    org_a = make_org(db, name="Org Alpha", subdomain="org-alpha-wr")
    org_b = make_org(db, name="Org Beta", subdomain="org-beta-wr")
    make_user(db, org_a, email="admin@alpha.com", role=RoleEnum.ADMIN)
    make_user(db, org_b, email="admin@beta.com", role=RoleEnum.ADMIN)
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()
            assert mock_send.call_count == 2


def test_recipients_are_only_admins_and_managers(db: Session):
    """
    STAFF users should never be in the recipients list for the weekly report.
    """
    org = make_org(db, name="Recipients Org", subdomain="recipients-wr")
    admin = make_user(db, org, email="admin@recipients.com", role=RoleEnum.ADMIN)
    manager = make_user(db, org, email="manager@recipients.com", role=RoleEnum.MANAGER)
    staff = make_user(db, org, email="staff@recipients.com", role=RoleEnum.STAFF)
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()

            mock_send.assert_called_once()
            recipients = (
                mock_send.call_args.kwargs.get("recipients")
                or mock_send.call_args.args[0]
            )
            assert admin.email in recipients
            assert manager.email in recipients
            assert staff.email not in recipients


def test_low_stock_products_included_correctly(db: Session):
    """
    Products below min_stock_level should appear in low_stock_products.
    Products at or above min should not.
    """
    org = make_org(db, name="Low Stock Report Org", subdomain="low-stock-wr")
    admin = make_user(db, org, email="admin@lowstockwr.com", role=RoleEnum.ADMIN)
    warehouse = make_warehouse(db, org.id, location="WR HQ")

    low_product = make_product(
        db, org.id, name="Low Widget", sku="SKU-LOW-WR", min_stock_level=10
    )
    ok_product = make_product(
        db, org.id, name="OK Widget", sku="SKU-OK-WR", min_stock_level=5
    )

    add_movement(
        db, org.id, low_product.id, warehouse.id, StockMovementTypeEnum.IN, 3, admin.id
    )  # 3 < 10
    add_movement(
        db, org.id, ok_product.id, warehouse.id, StockMovementTypeEnum.IN, 20, admin.id
    )  # 20 >= 5
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()

            low_stock_products = (
                mock_send.call_args.kwargs.get("low_stock_products")
                or mock_send.call_args.args[2]
            )
            low_ids = [str(p.product_id) for p in low_stock_products]
            assert str(low_product.id) in low_ids
            assert str(ok_product.id) not in low_ids


def test_pending_prs_includes_submitted_and_approved(db: Session):
    """
    pending_prs should include SUBMITTED and APPROVED requests.
    DRAFT, REJECTED, ORDERED should be excluded.
    """
    org = make_org(db, name="PR Status Org", subdomain="pr-status-wr")
    admin = make_user(db, org, email="admin@prstatus.com", role=RoleEnum.ADMIN)

    submitted = make_purchase_request(
        db, org.id, admin.id, PurchaseRequestStatusEnum.SUBMITTED, "PR-00001"
    )
    approved = make_purchase_request(
        db, org.id, admin.id, PurchaseRequestStatusEnum.APPROVED, "PR-00002"
    )
    draft = make_purchase_request(
        db, org.id, admin.id, PurchaseRequestStatusEnum.DRAFT, "PR-00003"
    )
    rejected = make_purchase_request(
        db, org.id, admin.id, PurchaseRequestStatusEnum.REJECTED, "PR-00004"
    )
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()

            pending_prs = (
                mock_send.call_args.kwargs.get("pending_prs")
                or mock_send.call_args.args[3]
            )
            pr_ids = [str(pr.id) for pr in pending_prs]
            assert str(submitted.id) in pr_ids
            assert str(approved.id) in pr_ids
            assert str(draft.id) not in pr_ids
            assert str(rejected.id) not in pr_ids


def test_movement_totals_only_include_last_7_days(db: Session):
    """
    Movements older than 7 days should not appear in the weekly totals.
    """
    org = make_org(db, name="Totals Org", subdomain="totals-wr")
    admin = make_user(db, org, email="admin@totals.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="Totals Widget", sku="SKU-TOTALS-WR", min_stock_level=0
    )
    warehouse = make_warehouse(db, org.id, location="Totals HQ")

    # Recent movement (2 days ago) — should be in totals
    add_movement(
        db,
        org.id,
        product.id,
        warehouse.id,
        StockMovementTypeEnum.IN,
        50,
        admin.id,
        days_ago=2,
    )
    # Old movement (10 days ago) — should NOT be in totals
    add_movement(
        db,
        org.id,
        product.id,
        warehouse.id,
        StockMovementTypeEnum.IN,
        999,
        admin.id,
        days_ago=10,
    )
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()

            totals = (
                mock_send.call_args.kwargs.get("totals") or mock_send.call_args.args[1]
            )
            in_total = totals.get(StockMovementTypeEnum.IN, 0)
            assert in_total == 50
            assert in_total != 999
            assert in_total != 1049  # 50 + 999 combined would mean old data leaked in


def test_no_error_when_org_has_no_data(db: Session):
    """
    An org with no movements, no PRs, and no products should not crash the job.
    """
    org = make_org(db, name="Empty Org WR", subdomain="empty-wr")
    make_user(db, org, email="admin@emptywr.com", role=RoleEnum.ADMIN)
    db.flush()

    with patch("app.jobs.weekly_report.SessionLocal", return_value=db):
        with patch("app.jobs.weekly_report.send_weekly_report") as mock_send:
            weekly_report()  # Should not raise
            mock_send.assert_called_once()
