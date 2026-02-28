"""
Tests for app/jobs/low_stock.py — check_low_stock()

Strategy:
- Uses the real test DB (via conftest.py fixtures)
- Patches SessionLocal to return the test session so check_low_stock
  uses the same transaction that gets rolled back after each test
- Test 1 uses real Resend — email will actually land at ielbanbuenawork@gmail.com
- Tests 2-5 mock send_low_stock_alert to avoid unnecessary emails

Run with:
    pytest tests/test_check_low_stock.py -v
"""

import uuid
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.jobs.low_stock import check_low_stock
from app.models.enums import RoleEnum, StockMovementTypeEnum
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.warehouse import Warehouse
from tests.conftest import make_org, make_user

# ── Helpers ────────────────────────────────────────────────────────────────────


def make_product(
    db: Session,
    org_id: uuid.UUID,
    name: str = "Test Widget",
    sku: str = "SKU-001",
    min_stock_level: int = 10,
) -> Product:
    product = Product(
        org_id=org_id,
        sku=sku,
        name=name,
        min_stock_level=min_stock_level,
    )
    db.add(product)
    db.flush()
    db.refresh(product)
    return product


def make_warehouse(
    db: Session,
    org_id: uuid.UUID,
    name: str = "Main Warehouse",
    location: str = "Test Location",
) -> Warehouse:
    warehouse = Warehouse(
        org_id=org_id,
        name=name,
        location=location,
    )
    db.add(warehouse)
    db.flush()
    db.refresh(warehouse)
    return warehouse


def add_stock_movement(
    db: Session,
    org_id: uuid.UUID,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    movement_type: StockMovementTypeEnum,
    quantity: int,
    created_by: uuid.UUID,
) -> StockMovement:
    movement = StockMovement(
        org_id=org_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        type=movement_type,
        quantity=quantity,
        created_by=created_by,
    )
    db.add(movement)
    db.flush()
    return movement


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_low_stock_sends_real_email(db: Session):
    """
    REAL EMAIL TEST — check your inbox at ielbanbuenawork@gmail.com.

    Stock in 15, out 12 → current = 3, min = 10.
    Should trigger a real Resend email.
    """
    org = make_org(db, name="Test Org", subdomain="test-org-low")
    admin = make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="Low Stock Widget", sku="SKU-LOW-001", min_stock_level=10
    )
    warehouse = make_warehouse(db, org.id, name="Warehouse A")

    add_stock_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.IN, 15, admin.id
    )
    add_stock_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.OUT, 12, admin.id
    )
    db.flush()

    with patch("app.jobs.low_stock.SessionLocal", return_value=db):
        check_low_stock(org_id=org.id, product_id=product.id, warehouse_id=warehouse.id)

    # No assertion needed — if no exception raised, job ran successfully.
    # Check ielbanbuenawork@gmail.com for the alert email.


def test_no_email_when_stock_is_above_minimum(db: Session):
    """
    Stock = 20, min = 10. No alert should fire.
    """
    org = make_org(db, name="Test Org 2", subdomain="test-org-ok")
    admin = make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="Healthy Widget", sku="SKU-OK-001", min_stock_level=10
    )
    warehouse = make_warehouse(db, org.id, name="Warehouse B")

    add_stock_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.IN, 20, admin.id
    )
    db.flush()

    with patch("app.jobs.low_stock.SessionLocal", return_value=db):
        with patch("app.jobs.low_stock.send_low_stock_alert") as mock_alert:
            check_low_stock(
                org_id=org.id, product_id=product.id, warehouse_id=warehouse.id
            )
            mock_alert.assert_not_called()


def test_no_email_when_stock_equals_minimum(db: Session):
    """
    Stock = 10, min = 10. Strict < comparison means no alert.
    """
    org = make_org(db, name="Test Org 3", subdomain="test-org-exact")
    admin = make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="Exact Min Widget", sku="SKU-EXACT-001", min_stock_level=10
    )
    warehouse = make_warehouse(db, org.id, name="Warehouse C")

    add_stock_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.IN, 10, admin.id
    )
    db.flush()

    with patch("app.jobs.low_stock.SessionLocal", return_value=db):
        with patch("app.jobs.low_stock.send_low_stock_alert") as mock_alert:
            check_low_stock(
                org_id=org.id, product_id=product.id, warehouse_id=warehouse.id
            )
            mock_alert.assert_not_called()


def test_no_stock_movements_returns_early(db: Session):
    """
    No movements exist for this product/warehouse combo.
    Should return early with no errors and no email.
    """
    org = make_org(db, name="Test Org 4", subdomain="test-org-empty")
    make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    product = make_product(
        db, org.id, name="No Movement Widget", sku="SKU-EMPTY-001", min_stock_level=5
    )
    warehouse = make_warehouse(db, org.id, name="Warehouse D")
    db.flush()

    with patch("app.jobs.low_stock.SessionLocal", return_value=db):
        with patch("app.jobs.low_stock.send_low_stock_alert") as mock_alert:
            check_low_stock(
                org_id=org.id, product_id=product.id, warehouse_id=warehouse.id
            )
            mock_alert.assert_not_called()


def test_only_admins_and_managers_are_recipients(db: Session):
    """
    STAFF users in the org should never appear in the email recipient list.
    Only ADMIN and MANAGER users should receive the alert.
    """
    org = make_org(db, name="Test Org 5", subdomain="test-org-roles")
    admin = make_user(db, org, email="ielbanbuenawork@gmail.com", role=RoleEnum.ADMIN)
    manager = make_user(db, org, email="manager@test.com", role=RoleEnum.MANAGER)
    staff = make_user(db, org, email="staff@test.com", role=RoleEnum.STAFF)

    product = make_product(
        db, org.id, name="Role Test Widget", sku="SKU-ROLE-001", min_stock_level=10
    )
    warehouse = make_warehouse(db, org.id, name="Warehouse E")

    # Stock = 3, below min of 10 — will trigger alert
    add_stock_movement(
        db, org.id, product.id, warehouse.id, StockMovementTypeEnum.IN, 3, admin.id
    )
    db.flush()

    with patch("app.jobs.low_stock.SessionLocal", return_value=db):
        with patch("app.jobs.low_stock.send_low_stock_alert") as mock_alert:
            check_low_stock(
                org_id=org.id, product_id=product.id, warehouse_id=warehouse.id
            )

            mock_alert.assert_called_once()
            call_args = mock_alert.call_args
            recipients = call_args.kwargs.get("recipients") or call_args.args[0]

            assert admin.email in recipients
            assert manager.email in recipients
            assert staff.email not in recipients
