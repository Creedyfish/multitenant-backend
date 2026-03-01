"""
Purchase request state machine tests.

State transitions map:
  DRAFT → SUBMITTED  (any role, owner only for STAFF)
  SUBMITTED → APPROVED (MANAGER/ADMIN only)
  SUBMITTED → REJECTED (MANAGER/ADMIN only)
  APPROVED → ORDERED   (any role)
  REJECTED → (terminal)
  ORDERED  → (terminal)

Covers:
- Create a PR → status is DRAFT
- STAFF can only see their own PRs
- MANAGER/ADMIN can see all PRs in org
- Edit a DRAFT PR (notes + items)
- Cannot edit a non-DRAFT PR → 422
- Submit DRAFT → SUBMITTED
- Cannot submit an already-SUBMITTED PR → 422
- MANAGER approves SUBMITTED → APPROVED, approved_by/approved_at set
- MANAGER rejects SUBMITTED → REJECTED, rejection_reason set
- Cannot approve an already-APPROVED PR → 422
- Cannot reject an already-REJECTED PR → 422
- Cannot reject a DRAFT directly → 422
- APPROVED → ORDERED via mark-ordered
- Cannot mark-order a SUBMITTED PR → 422
- Cannot mark-order a REJECTED PR → 422
- STAFF cannot view another user's PR → 403
- STAFF can view their own PR
- Audit log written for create, submit, approve, reject
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User
from tests.conftest import get_auth_headers, make_org, make_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def org(db: Session) -> Organization:
    return make_org(db, name="PR Org", subdomain="pr-org")


@pytest.fixture()
def admin(db: Session, org: Organization) -> User:
    return make_user(db, org, email="admin@pr.com", role=RoleEnum.ADMIN)


@pytest.fixture()
def manager(db: Session, org: Organization) -> User:
    return make_user(db, org, email="manager@pr.com", role=RoleEnum.MANAGER)


@pytest.fixture()
def staff(db: Session, org: Organization) -> User:
    return make_user(db, org, email="staff@pr.com", role=RoleEnum.STAFF)


@pytest.fixture()
def other_staff(db: Session, org: Organization) -> User:
    return make_user(db, org, email="other_staff@pr.com", role=RoleEnum.STAFF)


@pytest.fixture()
def admin_headers(client: TestClient, admin: User) -> dict[str, str]:
    return get_auth_headers(client, "admin@pr.com", "testpassword", "pr-org")


@pytest.fixture()
def manager_headers(client: TestClient, manager: User) -> dict[str, str]:
    return get_auth_headers(client, "manager@pr.com", "testpassword", "pr-org")


@pytest.fixture()
def staff_headers(client: TestClient, staff: User) -> dict[str, str]:
    return get_auth_headers(client, "staff@pr.com", "testpassword", "pr-org")


@pytest.fixture()
def other_staff_headers(client: TestClient, other_staff: User) -> dict[str, str]:
    return get_auth_headers(client, "other_staff@pr.com", "testpassword", "pr-org")


@pytest.fixture()
def product(db: Session, org: Organization) -> Product:
    p = Product(
        id=uuid.uuid4(),
        org_id=org.id,
        sku="PR-PROD-001",
        name="PR Product",
        min_stock_level=0,
    )
    db.add(p)
    db.flush()
    return p


# ── Helpers ───────────────────────────────────────────────────────────────────


def create_pr(
    client: TestClient,
    headers: dict[str, str],
    product_id: uuid.UUID,
    notes: str = "Need stuff",
) -> dict[str, Any]:
    response = client.post(
        "/purchase_requests/",
        json={
            "notes": notes,
            "items": [{"product_id": str(product_id), "quantity": 5}],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def submit_pr(
    client: TestClient,
    headers: dict[str, str],
    pr_id: str,
) -> dict[str, Any]:
    response = client.post(f"/purchase_requests/{pr_id}/submit", headers=headers)
    assert response.status_code == 200
    return response.json()


def approve_pr(
    client: TestClient,
    headers: dict[str, str],
    pr_id: str,
) -> dict[str, Any]:
    response = client.post(f"/purchase_requests/{pr_id}/approve", headers=headers)
    assert response.status_code == 200
    return response.json()


# ── Creation ──────────────────────────────────────────────────────────────────


class TestPurchaseRequestCreate:
    def test_create_pr_starts_as_draft(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        body = create_pr(client, staff_headers, product.id)
        assert body["status"] == "DRAFT"
        assert body["request_number"].startswith("PR-")
        assert len(body["items"]) == 1

    def test_create_pr_with_multiple_items(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        response = client.post(
            "/purchase_requests/",
            json={
                "notes": "Bulk order",
                "items": [
                    {"product_id": str(product.id), "quantity": 10},
                    {
                        "product_id": str(product.id),
                        "quantity": 5,
                        "estimated_price": "9.99",
                    },
                ],
            },
            headers=staff_headers,
        )
        assert response.status_code == 201
        assert len(response.json()["items"]) == 2

    def test_create_pr_without_items_returns_422(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
    ) -> None:
        response = client.post(
            "/purchase_requests/",
            json={"notes": "No items", "items": []},
            headers=staff_headers,
        )
        assert response.status_code == 422

    def test_create_pr_writes_audit_log(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        admin_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        audit = client.get(
            f"/audit_logs/?entity=PurchaseRequest&action=CREATE&entity_id={pr['id']}",
            headers=admin_headers,
        )
        assert audit.status_code == 200
        assert len(audit.json()) >= 1


# ── Visibility (STAFF vs MANAGER/ADMIN) ──────────────────────────────────────


class TestPurchaseRequestVisibility:
    def test_staff_only_sees_own_prs(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        other_staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        create_pr(client, staff_headers, product.id)
        create_pr(client, other_staff_headers, product.id)

        staff_list = client.get("/purchase_requests/", headers=staff_headers).json()
        assert len(staff_list) == 1

        manager_list = client.get("/purchase_requests/", headers=manager_headers).json()
        assert len(manager_list) >= 2

    def test_staff_can_view_own_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        response = client.get(f"/purchase_requests/{pr['id']}", headers=staff_headers)
        assert response.status_code == 200

    def test_staff_cannot_view_another_users_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        other_staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        response = client.get(
            f"/purchase_requests/{pr['id']}", headers=other_staff_headers
        )
        assert response.status_code == 403


# ── Editing ───────────────────────────────────────────────────────────────────


class TestPurchaseRequestEdit:
    def test_edit_draft_pr_notes(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        response = client.patch(
            f"/purchase_requests/{pr['id']}",
            json={"notes": "Updated notes"},
            headers=staff_headers,
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

    def test_edit_draft_replaces_items(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        response = client.patch(
            f"/purchase_requests/{pr['id']}",
            json={"items": [{"product_id": str(product.id), "quantity": 99}]},
            headers=staff_headers,
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["quantity"] == 99

    def test_cannot_edit_submitted_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        response = client.patch(
            f"/purchase_requests/{pr['id']}",
            json={"notes": "Should not work"},
            headers=staff_headers,
        )
        assert response.status_code == 422


# ── State machine transitions ─────────────────────────────────────────────────


class TestPurchaseRequestStateMachine:
    def test_submit_draft(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        result = submit_pr(client, staff_headers, pr["id"])
        assert result["status"] == "SUBMITTED"

    def test_cannot_submit_already_submitted_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/submit", headers=staff_headers
        )
        assert response.status_code == 422

    def test_cannot_submit_approved_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        approve_pr(client, manager_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/submit", headers=staff_headers
        )
        assert response.status_code == 422

    def test_approve_submitted_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        result = approve_pr(client, manager_headers, pr["id"])
        assert result["status"] == "APPROVED"
        assert result["approved_by"] is not None
        assert result["approved_at"] is not None

    def test_reject_submitted_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "Over budget"},
            headers=manager_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "REJECTED"
        assert body["rejection_reason"] == "Over budget"
        assert body["rejected_by"] is not None
        assert body["rejected_at"] is not None

    def test_cannot_approve_already_approved_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        approve_pr(client, manager_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/approve", headers=manager_headers
        )
        assert response.status_code == 422

    def test_cannot_reject_already_rejected_pr(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "First rejection"},
            headers=manager_headers,
        )
        response = client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "Second rejection"},
            headers=manager_headers,
        )
        assert response.status_code == 422

    def test_cannot_reject_draft_directly(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        response = client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "Premature"},
            headers=manager_headers,
        )
        assert response.status_code == 422

    def test_mark_ordered_from_approved(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        approve_pr(client, manager_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/mark-ordered",
            headers=manager_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ORDERED"

    def test_cannot_mark_ordered_from_submitted(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        response = client.post(
            f"/purchase_requests/{pr['id']}/mark-ordered",
            headers=manager_headers,
        )
        assert response.status_code == 422

    def test_cannot_mark_ordered_from_rejected(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "No budget"},
            headers=manager_headers,
        )
        response = client.post(
            f"/purchase_requests/{pr['id']}/mark-ordered",
            headers=manager_headers,
        )
        assert response.status_code == 422


# ── Audit log for PR transitions ──────────────────────────────────────────────


class TestPurchaseRequestAuditLog:
    def test_submit_writes_audit_log(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        admin_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        audit = client.get(
            f"/audit_logs/?entity=PurchaseRequest&action=SUBMIT&entity_id={pr['id']}",
            headers=admin_headers,
        )
        assert audit.status_code == 200
        assert len(audit.json()) >= 1

    def test_approve_writes_audit_log(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        admin_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        approve_pr(client, manager_headers, pr["id"])
        audit = client.get(
            f"/audit_logs/?entity=PurchaseRequest&action=APPROVE&entity_id={pr['id']}",
            headers=admin_headers,
        )
        assert audit.status_code == 200
        assert len(audit.json()) >= 1

    def test_reject_writes_audit_log(
        self,
        client: TestClient,
        staff_headers: dict[str, str],
        manager_headers: dict[str, str],
        admin_headers: dict[str, str],
        product: Product,
    ) -> None:
        pr = create_pr(client, staff_headers, product.id)
        submit_pr(client, staff_headers, pr["id"])
        client.post(
            f"/purchase_requests/{pr['id']}/reject",
            json={"rejection_reason": "Logging test"},
            headers=manager_headers,
        )
        audit = client.get(
            f"/audit_logs/?entity=PurchaseRequest&action=REJECT&entity_id={pr['id']}",
            headers=admin_headers,
        )
        assert audit.status_code == 200
        assert len(audit.json()) >= 1
