import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_auth_headers, make_org, make_user


@pytest.fixture()
def org(db: Session) -> Organization:
    return make_org(db, name="Test Org", subdomain="test-org")


@pytest.fixture()
def admin(db: Session, org: Organization) -> User:
    return make_user(db, org, email="admin@test.com", role=RoleEnum.ADMIN)


@pytest.fixture()
def auth_headers(client: TestClient, admin: User) -> dict[str, str]:
    return get_auth_headers(client, "admin@test.com", "testpassword", "test-org")


@pytest.fixture()
def tenant_headers(auth_headers: dict[str, str]) -> dict[str, str]:
    return {**auth_headers, "x-tenant-id": "test-org"}


# ── CRUD ──────────────────────────────────────────────────────────────────────


def test_create_product(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    response = client.post(
        "/products/",
        json={
            "sku": "SKU-001",
            "name": "Test Product",
            "category": "widgets",
            "min_stock_level": 10,
        },
        headers=tenant_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "SKU-001"
    assert data["name"] == "Test Product"


def test_get_products(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    client.post(
        "/products/",
        json={"sku": "SKU-002", "name": "Another Product", "min_stock_level": 5},
        headers=tenant_headers,
    )

    response = client.get("/products/", headers=tenant_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


def test_create_product_invalidates_cache(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    # Warm the cache
    client.get("/products/", headers=tenant_headers)

    # Create a new product — should invalidate cache
    client.post(
        "/products/",
        json={"sku": "SKU-003", "name": "New Product", "min_stock_level": 1},
        headers=tenant_headers,
    )

    # Next GET should reflect the new product
    response = client.get("/products/", headers=tenant_headers)
    skus = [p["sku"] for p in response.json()["items"]]
    assert "SKU-003" in skus


def test_get_single_product(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    created = client.post(
        "/products/",
        json={"sku": "SKU-004", "name": "Single Product", "min_stock_level": 0},
        headers=tenant_headers,
    ).json()

    response = client.get(f"/products/{created['id']}", headers=tenant_headers)
    assert response.status_code == 200
    assert response.json()["sku"] == "SKU-004"


def test_update_product(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    created = client.post(
        "/products/",
        json={"sku": "SKU-005", "name": "Before Update", "min_stock_level": 0},
        headers=tenant_headers,
    ).json()

    response = client.patch(
        f"/products/{created['id']}",
        json={"name": "After Update"},
        headers=tenant_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "After Update"


def test_delete_product(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    created = client.post(
        "/products/",
        json={"sku": "SKU-006", "name": "To Delete", "min_stock_level": 0},
        headers=tenant_headers,
    ).json()

    response = client.delete(f"/products/{created['id']}", headers=tenant_headers)
    assert response.status_code == 204

    response = client.get(f"/products/{created['id']}", headers=tenant_headers)
    assert response.status_code == 404


def test_duplicate_sku_rejected(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    client.post(
        "/products/",
        json={"sku": "SKU-007", "name": "Original", "min_stock_level": 0},
        headers=tenant_headers,
    )

    response = client.post(
        "/products/",
        json={"sku": "SKU-007", "name": "Duplicate", "min_stock_level": 0},
        headers=tenant_headers,
    )

    assert response.status_code == 409


# ── Cache ─────────────────────────────────────────────────────────────────────


def test_cache_miss_then_hit(
    client: TestClient, tenant_headers: dict[str, str], org: Organization
):
    client.post(
        "/products/",
        json={"sku": "SKU-CACHE", "name": "Cache Test Product", "min_stock_level": 0},
        headers=tenant_headers,
    )

    with patch("app.core.cache.redis_client") as mock_redis:
        # First call — cache miss
        mock_redis.get.return_value = None

        r1 = client.get("/products/", headers=tenant_headers)
        assert r1.status_code == 200

        # Assert we read from Redis and then wrote to it
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()

        # Second call — cache hit
        mock_redis.get.return_value = json.dumps(r1.json())
        mock_redis.setex.reset_mock()

        r2 = client.get("/products/", headers=tenant_headers)
        assert r2.status_code == 200

        # Assert Redis was read but DB was skipped (no setex)
        mock_redis.get.assert_called()
        mock_redis.setex.assert_not_called()
        assert r1.json() == r2.json()
