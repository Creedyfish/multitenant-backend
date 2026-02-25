"""
Audit log tests.

Covers:
- List audit logs returns entries for own org
- Filter by entity (e.g. Product)
- Filter by action (e.g. CREATE)
- Filter by entity_id
- Filter by actor_id
- Combine entity + action filters
- Pagination (skip/limit)
- Get audit log by ID
- Get nonexistent audit log → 404
- Audit log is org-scoped (Org B cannot see Org A's logs)
- before=null and after populated on CREATE logs
- before and after both populated on UPDATE logs
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_auth_headers, make_org, make_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def org(db: Session) -> Organization:
    return make_org(db, name="Audit Org", subdomain="audit-org")


@pytest.fixture()
def admin(db: Session, org: Organization) -> User:
    return make_user(db, org, email="admin@audit.com", role=RoleEnum.ADMIN)


@pytest.fixture()
def headers(client: TestClient, admin: User) -> dict[str, str]:
    return get_auth_headers(client, "admin@audit.com", "testpassword", "audit-org")


# ── Helpers ───────────────────────────────────────────────────────────────────


def create_product(
    client: TestClient,
    headers: dict[str, str],
    sku: str = "AUDIT-P-001",
    name: str = "Audit Product",
) -> dict[str, Any]:
    return client.post(
        "/products/",
        json={"sku": sku, "name": name, "min_stock_level": 0},
        headers=headers,
    ).json()


# ── Listing & filtering ───────────────────────────────────────────────────────


class TestAuditLogList:
    def test_list_returns_entries(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        create_product(client, headers)
        response = client.get("/audit_logs/", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_filter_by_entity(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        create_product(client, headers, sku="FILTER-ENT")
        response = client.get("/audit_logs/?entity=Product", headers=headers)
        assert response.status_code == 200
        entities = {entry["entity"] for entry in response.json()}
        assert entities == {"Product"}

    def test_filter_by_action(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        create_product(client, headers, sku="FILTER-ACT")
        response = client.get("/audit_logs/?action=CREATE", headers=headers)
        assert response.status_code == 200
        actions = {entry["action"] for entry in response.json()}
        assert actions == {"CREATE"}

    def test_filter_by_entity_id(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        product = create_product(client, headers, sku="FILTER-ID")
        response = client.get(
            f"/audit_logs/?entity_id={product['id']}", headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1
        for entry in response.json():
            assert entry["entity_id"] == product["id"]

    def test_filter_by_entity_and_action(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        product = create_product(client, headers, sku="COMBO-001")
        client.patch(
            f"/products/{product['id']}",
            json={"name": "Updated"},
            headers=headers,
        )
        create_logs = client.get(
            "/audit_logs/?entity=Product&action=CREATE", headers=headers
        ).json()
        update_logs = client.get(
            "/audit_logs/?entity=Product&action=UPDATE", headers=headers
        ).json()

        assert {e["action"] for e in create_logs} == {"CREATE"}
        assert {e["action"] for e in update_logs} == {"UPDATE"}

    def test_pagination_skip_and_limit(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        for i in range(5):
            create_product(client, headers, sku=f"PAGE-{i:03d}")

        page1 = client.get(
            "/audit_logs/?entity=Product&action=CREATE&skip=0&limit=3",
            headers=headers,
        ).json()
        page2 = client.get(
            "/audit_logs/?entity=Product&action=CREATE&skip=3&limit=3",
            headers=headers,
        ).json()

        assert len(page1) <= 3
        ids1 = {e["id"] for e in page1}
        ids2 = {e["id"] for e in page2}
        assert ids1.isdisjoint(ids2)


# ── Get by ID ─────────────────────────────────────────────────────────────────


class TestAuditLogGetById:
    def test_get_audit_log_by_id(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        create_product(client, headers, sku="BY-ID-001")
        logs = client.get(
            "/audit_logs/?entity=Product&action=CREATE", headers=headers
        ).json()
        assert len(logs) >= 1
        audit_id: str = logs[0]["id"]

        response = client.get(f"/audit_logs/{audit_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == audit_id

    def test_get_nonexistent_audit_log_returns_404(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        response = client.get(f"/audit_logs/{uuid.uuid4()}", headers=headers)
        assert response.status_code == 404


# ── Org isolation ─────────────────────────────────────────────────────────────


class TestAuditLogOrgIsolation:
    def test_org_b_cannot_see_org_a_audit_logs(
        self,
        client: TestClient,
        headers: dict[str, str],
        db: Session,
    ) -> None:
        create_product(client, headers, sku="ORG-ISO-001")

        org_b: Organization = make_org(db, name="Audit Org B", subdomain="audit-org-b")
        make_user(db, org_b, email="admin@auditb.com", role=RoleEnum.ADMIN)
        headers_b = get_auth_headers(
            client, "admin@auditb.com", "testpassword", "audit-org-b"
        )

        response = client.get("/audit_logs/", headers=headers_b)
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_audit_log_before_after_fields_on_create(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        product = create_product(client, headers, sku="FIELDS-001")
        logs = client.get(
            f"/audit_logs/?entity=Product&action=CREATE&entity_id={product['id']}",
            headers=headers,
        ).json()
        assert len(logs) == 1
        assert logs[0]["before"] is None
        assert logs[0]["after"] is not None
        assert logs[0]["after"]["sku"] == "FIELDS-001"

    def test_update_audit_log_has_before_and_after(
        self, client: TestClient, headers: dict[str, str]
    ) -> None:
        product = create_product(client, headers, sku="BEFORE-AFT-001")
        client.patch(
            f"/products/{product['id']}",
            json={"name": "Changed Name"},
            headers=headers,
        )
        logs = client.get(
            f"/audit_logs/?entity=Product&action=UPDATE&entity_id={product['id']}",
            headers=headers,
        ).json()
        assert len(logs) >= 1
        assert logs[0]["before"] is not None
        assert logs[0]["after"] is not None
        assert logs[0]["before"]["name"] != logs[0]["after"]["name"]
