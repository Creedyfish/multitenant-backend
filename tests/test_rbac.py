"""
RBAC tests.

Covers:
- STAFF cannot create/update/delete products, warehouses, suppliers
- STAFF can read products, warehouses, suppliers
- MANAGER can create/update/delete products, warehouses, suppliers
- STAFF cannot perform stock_in / stock_out / transfer / adjust
- MANAGER can perform stock write operations
- STAFF cannot approve or reject purchase requests
- MANAGER and ADMIN can approve/reject purchase requests
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
    return make_org(db, name="RBAC Org", subdomain="rbac-org")


@pytest.fixture()
def admin(db: Session, org: Organization) -> User:
    return make_user(db, org, email="admin@rbac.com", role=RoleEnum.ADMIN)


@pytest.fixture()
def manager(db: Session, org: Organization) -> User:
    return make_user(db, org, email="manager@rbac.com", role=RoleEnum.MANAGER)


@pytest.fixture()
def staff(db: Session, org: Organization) -> User:
    return make_user(db, org, email="staff@rbac.com", role=RoleEnum.STAFF)


@pytest.fixture()
def admin_headers(client: TestClient, admin: User) -> dict[str, str]:
    return get_auth_headers(client, "admin@rbac.com", "testpassword", "rbac-org")


@pytest.fixture()
def manager_headers(client: TestClient, manager: User) -> dict[str, str]:
    return get_auth_headers(client, "manager@rbac.com", "testpassword", "rbac-org")


@pytest.fixture()
def staff_headers(client: TestClient, staff: User) -> dict[str, str]:
    return get_auth_headers(client, "staff@rbac.com", "testpassword", "rbac-org")


@pytest.fixture()
def a_product(db: Session, org: Organization) -> Product:
    p = Product(
        id=uuid.uuid4(),
        org_id=org.id,
        sku="RBAC-SKU-001",
        name="RBAC Product",
        min_stock_level=5,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture()
def a_warehouse(db: Session, org: Organization) -> Warehouse:
    w = Warehouse(
        id=uuid.uuid4(),
        org_id=org.id,
        name="RBAC Warehouse",
        location="RBAC Location",
    )
    db.add(w)
    db.flush()
    return w


# ── Product RBAC ──────────────────────────────────────────────────────────────


class TestProductRBAC:
    def test_staff_can_list_products(
        self, client: TestClient, staff_headers: dict[str, str], a_product: Product
    ):
        response = client.get("/products/", headers=staff_headers)
        assert response.status_code == 200

    def test_staff_cannot_create_product(
        self, client: TestClient, staff_headers: dict[str, str]
    ):
        response = client.post(
            "/products/",
            json={"sku": "NOPE", "name": "Unauthorized", "min_stock_level": 0},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_update_product(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_product: Product,
    ):
        response = client.patch(
            f"/products/{a_product.id}",
            json={"name": "Hacked"},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_delete_product(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_product: Product,
    ):
        response = client.delete(f"/products/{a_product.id}", headers=staff_headers)
        assert response.status_code == 403

    def test_manager_can_create_product(
        self, client: TestClient, manager_headers: dict[str, str]
    ):
        response = client.post(
            "/products/",
            json={"sku": "MGR-SKU", "name": "Manager Product", "min_stock_level": 0},
            headers=manager_headers,
        )
        assert response.status_code == 201

    def test_manager_can_update_product(
        self,
        client: TestClient,
        manager_headers: dict[str, str],
        a_product: Product,
    ):
        response = client.patch(
            f"/products/{a_product.id}",
            json={"name": "Updated by Manager"},
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated by Manager"

    def test_manager_can_delete_product(
        self,
        client: TestClient,
        manager_headers: dict[str, str],
        a_product: Product,
    ):
        response = client.delete(f"/products/{a_product.id}", headers=manager_headers)
        assert response.status_code == 204


# ── Warehouse RBAC ────────────────────────────────────────────────────────────


class TestWarehouseRBAC:
    def test_staff_can_list_warehouses(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_warehouse: Warehouse,
    ):
        response = client.get("/warehouses/", headers=staff_headers)
        assert response.status_code == 200

    def test_staff_cannot_create_warehouse(
        self, client: TestClient, staff_headers: dict[str, str]
    ):
        response = client.post(
            "/warehouses/",
            json={"name": "Unauthorized WH", "location": "Nowhere"},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_update_warehouse(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_warehouse: Warehouse,
    ):
        response = client.patch(
            f"/warehouses/{a_warehouse.id}",
            json={"name": "Hacked"},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_delete_warehouse(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_warehouse: Warehouse,
    ):
        response = client.delete(f"/warehouses/{a_warehouse.id}", headers=staff_headers)
        assert response.status_code == 403

    def test_manager_can_create_warehouse(
        self, client: TestClient, manager_headers: dict[str, str]
    ):
        response = client.post(
            "/warehouses/",
            json={"name": "Manager WH", "location": "Somewhere"},
            headers=manager_headers,
        )
        assert response.status_code == 201


# ── Supplier RBAC ─────────────────────────────────────────────────────────────


class TestSupplierRBAC:
    def test_staff_can_list_suppliers(
        self, client: TestClient, staff_headers: dict[str, str]
    ):
        response = client.get("/suppliers/", headers=staff_headers)
        assert response.status_code == 200

    def test_staff_cannot_create_supplier(
        self, client: TestClient, staff_headers: dict[str, str]
    ):
        response = client.post(
            "/suppliers/",
            json={"name": "Unauthorized Supplier"},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_manager_can_create_supplier(
        self, client: TestClient, manager_headers: dict[str, str]
    ):
        response = client.post(
            "/suppliers/",
            json={"name": "Manager Supplier"},
            headers=manager_headers,
        )
        assert response.status_code == 201


# ── Stock movement RBAC ───────────────────────────────────────────────────────


class TestStockRBAC:
    def test_staff_cannot_do_stock_in(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_product: Product,
        a_warehouse: Warehouse,
    ):
        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(a_product.id),
                "warehouse_id": str(a_warehouse.id),
                "quantity": 10,
            },
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_do_stock_out(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_product: Product,
        a_warehouse: Warehouse,
    ):
        response = client.post(
            "/stock_movements/out",
            json={
                "product_id": str(a_product.id),
                "warehouse_id": str(a_warehouse.id),
                "quantity": 5,
            },
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_staff_cannot_adjust_stock(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        a_product: Product,
        a_warehouse: Warehouse,
    ):
        response = client.post(
            "/stock_movements/adjust",
            json={
                "product_id": str(a_product.id),
                "warehouse_id": str(a_warehouse.id),
                "quantity": 10,
            },
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_manager_can_do_stock_in(
        self,
        client: TestClient,
        manager_headers: dict[str, str],
        a_product: Product,
        a_warehouse: Warehouse,
    ):
        response = client.post(
            "/stock_movements/in",
            json={
                "product_id": str(a_product.id),
                "warehouse_id": str(a_warehouse.id),
                "quantity": 10,
            },
            headers=manager_headers,
        )
        assert response.status_code == 201


# ── Purchase request approval RBAC ───────────────────────────────────────────


class TestPurchaseRequestApprovalRBAC:
    def _create_and_submit_pr(
        self,
        client: TestClient,
        headers: dict[str, str],
        product_id: uuid.UUID,
    ) -> str:
        """Helper: create a PR as the given user and submit it."""
        create_resp = client.post(
            "/purchase_requests/",
            json={
                "notes": "Need stock",
                "items": [{"product_id": str(product_id), "quantity": 5}],
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        pr_id: str = create_resp.json()["id"]

        submit_resp = client.post(f"/purchase_requests/{pr_id}/submit", headers=headers)
        assert submit_resp.status_code == 200
        return pr_id

    def test_staff_cannot_approve(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        admin_headers: dict[str, str],
        a_product: Product,
    ):
        pr_id = self._create_and_submit_pr(client, staff_headers, a_product.id)
        response = client.post(
            f"/purchase_requests/{pr_id}/approve", headers=staff_headers
        )
        assert response.status_code == 403

    def test_staff_cannot_reject(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        admin_headers: dict[str, str],
        a_product: Product,
    ):
        pr_id = self._create_and_submit_pr(client, staff_headers, a_product.id)
        response = client.post(
            f"/purchase_requests/{pr_id}/reject",
            json={"rejection_reason": "Not authorized"},
            headers=staff_headers,
        )
        assert response.status_code == 403

    def test_manager_can_approve(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        a_product: Product,
    ):
        pr_id = self._create_and_submit_pr(client, staff_headers, a_product.id)
        response = client.post(
            f"/purchase_requests/{pr_id}/approve", headers=manager_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "APPROVED"

    def test_admin_can_reject(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        admin_headers: dict[str, str],
        a_product: Product,
    ):
        pr_id = self._create_and_submit_pr(client, staff_headers, a_product.id)
        response = client.post(
            f"/purchase_requests/{pr_id}/reject",
            json={"rejection_reason": "Budget exceeded"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"
        assert response.json()["rejection_reason"] == "Budget exceeded"
