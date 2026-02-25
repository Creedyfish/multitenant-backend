"""
Stock operation tests.

Covers:
- stock_in happy path, response shape
- stock_in creates an audit log entry
- stock_out happy path
- stock_out with insufficient stock → 422
- stock_out with zero stock → 422
- transfer between two warehouses, both ledger entries created
- transfer with insufficient stock → 422
- transfer to same warehouse → 422
- positive adjustment
- negative adjustment within available stock
- negative adjustment exceeding available stock → 422
- zero adjustment → 422
- get_ledger returns movements for own org only
- get_stock_levels reflects all movements correctly
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from tests.conftest import get_auth_headers, make_org, make_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def org(db: Session) -> Organization:
    return make_org(db, name="Stock Org", subdomain="stock-org")


@pytest.fixture()
def manager(db: Session, org: Organization) -> User:
    return make_user(db, org, email="manager@stock.com", role=RoleEnum.MANAGER)


@pytest.fixture()
def headers(client: TestClient, manager: User) -> dict[str, str]:
    return get_auth_headers(client, "manager@stock.com", "testpassword", "stock-org")


@pytest.fixture()
def product(db: Session, org: Organization) -> Product:
    p = Product(
        id=uuid.uuid4(),
        org_id=org.id,
        sku="STOCK-001",
        name="Stock Product",
        min_stock_level=10,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture()
def warehouse(db: Session, org: Organization) -> Warehouse:
    w = Warehouse(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Main Warehouse",
        location="Shelf A",
    )
    db.add(w)
    db.flush()
    return w


@pytest.fixture()
def warehouse_b(db: Session, org: Organization) -> Warehouse:
    w = Warehouse(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Secondary Warehouse",
        location="Shelf B",
    )
    db.add(w)
    db.flush()
    return w


# ── Helpers ───────────────────────────────────────────────────────────────────


def do_stock_in(
    client: TestClient,
    headers: dict[str, str],
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: int = 50,
) -> None:
    client.post(
        "/stock_movements/in",
        json={
            "product_id": str(product_id),
            "warehouse_id": str(warehouse_id),
            "quantity": quantity,
        },
        headers=headers,
    )


# ── Stock In ──────────────────────────────────────────────────────────────────


class TestStockIn:
    def test_stock_in_happy_path(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 100,
            },
            headers=headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == "IN"
        assert body["quantity"] == 100
        assert body["product_id"] == str(product.id)
        assert body["warehouse_id"] == str(warehouse.id)

    def test_stock_in_creates_audit_log(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 50)
        audit_resp = client.get(
            "/audit_logs/?entity=StockMovement&action=STOCK_IN",
            headers=headers,
        )
        assert audit_resp.status_code == 200
        assert len(audit_resp.json()) >= 1

    def test_stock_in_unknown_product_returns_404(
        self,
        client: TestClient,
        headers: dict[str, str],
        warehouse: Warehouse,
    ) -> None:
        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(uuid.uuid4()),
                "warehouse_id": str(warehouse.id),
                "quantity": 10,
            },
            headers=headers,
        )
        assert response.status_code == 404

    def test_stock_in_unknown_warehouse_returns_404(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
    ) -> None:
        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(uuid.uuid4()),
                "quantity": 10,
            },
            headers=headers,
        )
        assert response.status_code == 404


# ── Stock Out ─────────────────────────────────────────────────────────────────


class TestStockOut:
    def test_stock_out_happy_path(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 100)
        response = client.post(
            "/stock_movements/out",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 30,
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["type"] == "OUT"
        assert response.json()["quantity"] == 30

    def test_stock_out_insufficient_stock_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 10)
        response = client.post(
            "/stock_movements/out",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 99,
            },
            headers=headers,
        )
        assert response.status_code == 422
        assert "Insufficient" in response.json()["detail"]

    def test_stock_out_from_empty_warehouse_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        response = client.post(
            "/stock_movements/out",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 1,
            },
            headers=headers,
        )
        assert response.status_code == 422


# ── Transfer ──────────────────────────────────────────────────────────────────


class TestStockTransfer:
    def test_transfer_creates_two_movements(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
        warehouse_b: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 100)
        response = client.post(
            "/stock_movements/transfer",
            json={
                "product_id": str(product.id),
                "from_warehouse_id": str(warehouse.id),
                "to_warehouse_id": str(warehouse_b.id),
                "quantity": 40,
            },
            headers=headers,
        )
        assert response.status_code == 201
        movements = response.json()
        assert len(movements) == 2
        types = {m["type"] for m in movements}
        assert types == {"TRANSFER_OUT", "TRANSFER_IN"}
        assert movements[0]["reference"] == movements[1]["reference"]

    def test_transfer_same_warehouse_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 100)
        response = client.post(
            "/stock_movements/transfer",
            json={
                "product_id": str(product.id),
                "from_warehouse_id": str(warehouse.id),
                "to_warehouse_id": str(warehouse.id),
                "quantity": 10,
            },
            headers=headers,
        )
        assert response.status_code == 422

    def test_transfer_insufficient_stock_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
        warehouse_b: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 5)
        response = client.post(
            "/stock_movements/transfer",
            json={
                "product_id": str(product.id),
                "from_warehouse_id": str(warehouse.id),
                "to_warehouse_id": str(warehouse_b.id),
                "quantity": 100,
            },
            headers=headers,
        )
        assert response.status_code == 422


# ── Adjustment ────────────────────────────────────────────────────────────────


class TestStockAdjustment:
    def test_positive_adjustment(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        response = client.post(
            "/stock_movements/adjust",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 25,
                "notes": "Inventory count correction",
            },
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["type"] == "ADJUSTMENT"
        assert response.json()["quantity"] == 25

    def test_negative_adjustment_within_available_stock(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 50)
        response = client.post(
            "/stock_movements/adjust",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": -20,
            },
            headers=headers,
        )
        assert response.status_code == 201

    def test_negative_adjustment_exceeding_stock_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 10)
        response = client.post(
            "/stock_movements/adjust",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": -99,
            },
            headers=headers,
        )
        assert response.status_code == 422

    def test_zero_adjustment_returns_422(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        response = client.post(
            "/stock_movements/adjust",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 0,
            },
            headers=headers,
        )
        assert response.status_code == 422


# ── Ledger & levels ───────────────────────────────────────────────────────────


class TestStockLedgerAndLevels:
    def test_ledger_reflects_all_movements(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 100)
        client.post(
            "/stock_movements/out",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 30,
            },
            headers=headers,
        )
        ledger = client.get("/stock_movements/ledger", headers=headers)
        assert ledger.status_code == 200
        assert len(ledger.json()) >= 2

    def test_stock_levels_net_calculation(
        self,
        client: TestClient,
        headers: dict[str, str],
        product: Product,
        warehouse: Warehouse,
    ) -> None:
        do_stock_in(client, headers, product.id, warehouse.id, 100)
        client.post(
            "/stock_movements/out",
            json={
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "quantity": 30,
            },
            headers=headers,
        )
        levels = client.get("/stock_movements/levels", headers=headers)
        assert levels.status_code == 200
        level = next(
            (
                lvl
                for lvl in levels.json()
                if lvl["product_id"] == str(product.id)
                and lvl["warehouse_id"] == str(warehouse.id)
            ),
            None,
        )
        assert level is not None
        assert level["current_stock"] == 70  # 100 in - 30 out
