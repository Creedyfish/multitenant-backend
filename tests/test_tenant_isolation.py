"""
Cross-tenant isolation tests.

Verifies that users from Org A can never read, modify, or delete
resources belonging to Org B, and vice versa.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from tests.conftest import get_auth_headers

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def headers_a(client: TestClient, user_a: User) -> dict[str, str]:
    return get_auth_headers(client, "user@orga.com", "testpassword", "org-a")


@pytest.fixture()
def headers_b(client: TestClient, user_b: User) -> dict[str, str]:
    return get_auth_headers(client, "user@orgb.com", "testpassword", "org-b")


@pytest.fixture()
def product_in_org_a(db: Session, org_a: Organization) -> Product:
    product = Product(
        id=uuid.uuid4(),
        org_id=org_a.id,
        sku="SKU-A-001",
        name="Org A Product",
        min_stock_level=10,
    )
    db.add(product)
    db.flush()
    return product


@pytest.fixture()
def product_in_org_b(db: Session, org_b: Organization) -> Product:
    product = Product(
        id=uuid.uuid4(),
        org_id=org_b.id,
        sku="SKU-B-001",
        name="Org B Product",
        min_stock_level=5,
    )
    db.add(product)
    db.flush()
    return product


@pytest.fixture()
def warehouse_in_org_a(db: Session, org_a: Organization) -> Warehouse:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        org_id=org_a.id,
        name="Org A Warehouse",
        location="Location A",
    )
    db.add(warehouse)
    db.flush()
    return warehouse


# ── Product isolation ─────────────────────────────────────────────────────────


class TestProductIsolation:
    def test_user_a_cannot_see_org_b_products(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        product_in_org_b: Product,
    ):
        """Listing products as Org A should never return Org B's products."""
        response = client.get("/products/", headers=headers_a)
        assert response.status_code == 200
        ids = [p["id"] for p in response.json()]
        assert str(product_in_org_b.id) not in ids

    def test_user_a_cannot_fetch_org_b_product_by_id(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        product_in_org_b: Product,
    ):
        """Directly fetching Org B's product ID as Org A should return 404."""
        response = client.get(f"/products/{product_in_org_b.id}", headers=headers_a)
        assert response.status_code == 404

    def test_user_a_cannot_update_org_b_product(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        product_in_org_b: Product,
    ):
        response = client.patch(
            f"/products/{product_in_org_b.id}",
            json={"name": "Hacked"},
            headers=headers_a,
        )
        assert response.status_code == 404

    def test_user_a_cannot_delete_org_b_product(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        product_in_org_b: Product,
    ):
        response = client.delete(f"/products/{product_in_org_b.id}", headers=headers_a)
        assert response.status_code == 404

    def test_each_org_only_sees_own_products(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        headers_b: dict[str, str],
        product_in_org_a: Product,
        product_in_org_b: Product,
    ):
        """Each org's product list is completely disjoint."""
        resp_a = client.get("/products/", headers=headers_a)
        resp_b = client.get("/products/", headers=headers_b)

        ids_a = {p["id"] for p in resp_a.json()}
        ids_b = {p["id"] for p in resp_b.json()}

        assert str(product_in_org_a.id) in ids_a
        assert str(product_in_org_b.id) not in ids_a

        assert str(product_in_org_b.id) in ids_b
        assert str(product_in_org_a.id) not in ids_b


# ── Warehouse isolation ───────────────────────────────────────────────────────


class TestWarehouseIsolation:
    def test_user_b_cannot_see_org_a_warehouses(
        self,
        client: TestClient,
        headers_b: dict[str, str],
        warehouse_in_org_a: Warehouse,
    ):
        response = client.get("/warehouses/", headers=headers_b)
        assert response.status_code == 200
        ids = [w["id"] for w in response.json()]
        assert str(warehouse_in_org_a.id) not in ids

    def test_user_b_cannot_fetch_org_a_warehouse_by_id(
        self,
        client: TestClient,
        headers_b: dict[str, str],
        warehouse_in_org_a: Warehouse,
    ):
        response = client.get(f"/warehouses/{warehouse_in_org_a.id}", headers=headers_b)
        assert response.status_code == 404


# ── Stock isolation ───────────────────────────────────────────────────────────


class TestStockIsolation:
    def test_user_a_cannot_stock_in_to_org_b_warehouse(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        product_in_org_a: Product,
        db: Session,
        org_b: Organization,
    ):
        """Org A user trying to move stock into an Org B warehouse should fail."""
        org_b_warehouse = Warehouse(
            id=uuid.uuid4(),
            org_id=org_b.id,
            name="Org B Warehouse",
            location="Location B",
        )
        db.add(org_b_warehouse)
        db.flush()

        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(product_in_org_a.id),
                "warehouse_id": str(org_b_warehouse.id),
                "quantity": 10,
            },
            headers=headers_a,
        )
        # Should fail because the warehouse doesn't belong to Org A
        assert response.status_code in (403, 404, 422)

    def test_stock_ledger_only_returns_own_org_movements(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        headers_b: dict[str, str],
        product_in_org_a: Product,
        warehouse_in_org_a: Warehouse,
    ):
        """Stock ledger for Org A should never contain Org B movements."""
        # Create a stock movement for Org A
        client.post(
            "/stock_movements/in",
            json={
                "product_id": str(product_in_org_a.id),
                "warehouse_id": str(warehouse_in_org_a.id),
                "quantity": 50,
            },
            headers=headers_a,
        )

        # Org B queries the ledger — should see nothing from Org A
        resp_b = client.get("/stock_movements/ledger", headers=headers_b)
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0


# ── SKU uniqueness is per-org, not global ─────────────────────────────────────


class TestSkuIsolation:
    def test_same_sku_allowed_across_orgs(
        self,
        client: TestClient,
        headers_a: dict[str, str],
        headers_b: dict[str, str],
    ):
        """Two different orgs can have the same SKU without conflict."""
        payload: dict[str, str | int] = {
            "sku": "SHARED-SKU",
            "name": "Widget",
            "min_stock_level": 0,
        }

        resp_a = client.post("/products/", json=payload, headers=headers_a)
        resp_b = client.post("/products/", json=payload, headers=headers_b)

        assert resp_a.status_code == 201
        assert resp_b.status_code == 201
        # They should be different products
        assert resp_a.json()["id"] != resp_b.json()["id"]

    def test_duplicate_sku_within_same_org_is_rejected(
        self,
        client: TestClient,
        headers_a: dict[str, str],
    ):
        payload: dict[str, str | int] = {
            "sku": "DUPE-SKU",
            "name": "Widget",
            "min_stock_level": 0,
        }

        client.post("/products/", json=payload, headers=headers_a)
        response = client.post("/products/", json=payload, headers=headers_a)

        assert response.status_code in (400, 409, 422)
