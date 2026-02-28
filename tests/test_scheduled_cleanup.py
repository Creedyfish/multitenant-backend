"""
Tests for app/jobs/cleanup.py — scheduled_cleanup()

Strategy:
- Patches SessionLocal to use the test DB session
- Backdates created_at directly via SQL to simulate old records
- All changes roll back after each test

Run with:
    pytest tests/test_scheduled_cleanup.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.jobs.cleanup import scheduled_cleanup
from app.models.enums import PurchaseRequestStatusEnum
from app.models.purchase_request import PurchaseRequest
from tests.conftest import make_org, make_user

# ── Helpers ────────────────────────────────────────────────────────────────────


def make_purchase_request(
    db: Session,
    org_id: uuid.UUID,
    created_by: uuid.UUID,
    status: PurchaseRequestStatusEnum = PurchaseRequestStatusEnum.DRAFT,
    request_number: str = "PR-00001",
) -> PurchaseRequest:
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


def backdate(db: Session, pr: PurchaseRequest, days: int):
    """Set created_at to `days` ago directly in the DB."""
    old_date = datetime.now(timezone.utc) - timedelta(days=days)
    db.execute(
        text("UPDATE purchase_requests SET created_at = :d WHERE id = :id"),
        {"d": old_date, "id": pr.id},
    )
    db.flush()


def exists(db: Session, pr_id: uuid.UUID) -> bool:
    """Query by ID after expire_all to avoid DetachedInstanceError.

    scheduled_cleanup calls db.close() in its finally block which detaches
    all objects. We can't use db.get() after that — must re-query by ID.
    """
    db.expire_all()
    return (
        db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == pr_id)
        ).scalar_one_or_none()
        is not None
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_deletes_draft_older_than_30_days(db: Session):
    """
    A DRAFT PR created 31 days ago should be deleted by scheduled_cleanup.
    """
    org = make_org(db, name="Cleanup Org 1", subdomain="cleanup-org-1")
    user = make_user(db, org, email="user@cleanup1.com")
    pr = make_purchase_request(db, org.id, user.id, request_number="PR-00001")
    pr_id = pr.id
    backdate(db, pr, days=31)

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()

    assert not exists(db, pr_id)


def test_does_not_delete_draft_within_30_days(db: Session):
    """
    A DRAFT PR created 10 days ago should NOT be deleted.
    """
    org = make_org(db, name="Cleanup Org 2", subdomain="cleanup-org-2")
    user = make_user(db, org, email="user@cleanup2.com")
    pr = make_purchase_request(db, org.id, user.id, request_number="PR-00001")
    pr_id = pr.id
    backdate(db, pr, days=10)

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()

    assert exists(db, pr_id)


def test_does_not_delete_submitted_pr_older_than_30_days(db: Session):
    """
    Only DRAFT status should be deleted. A SUBMITTED PR older than 30 days
    should be left alone.
    """
    org = make_org(db, name="Cleanup Org 3", subdomain="cleanup-org-3")
    user = make_user(db, org, email="user@cleanup3.com")
    pr = make_purchase_request(
        db,
        org.id,
        user.id,
        status=PurchaseRequestStatusEnum.SUBMITTED,
        request_number="PR-00001",
    )
    pr_id = pr.id
    backdate(db, pr, days=31)

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()

    assert exists(db, pr_id)


def test_does_not_delete_approved_pr_older_than_30_days(db: Session):
    """
    APPROVED PRs older than 30 days should never be deleted.
    """
    org = make_org(db, name="Cleanup Org 4", subdomain="cleanup-org-4")
    user = make_user(db, org, email="user@cleanup4.com")
    pr = make_purchase_request(
        db,
        org.id,
        user.id,
        status=PurchaseRequestStatusEnum.APPROVED,
        request_number="PR-00001",
    )
    pr_id = pr.id
    backdate(db, pr, days=35)

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()

    assert exists(db, pr_id)


def test_deletes_multiple_stale_drafts(db: Session):
    """
    All stale DRAFT PRs should be cleaned up in one run.
    Recent DRAFTs should be preserved.
    """
    org = make_org(db, name="Cleanup Org 5", subdomain="cleanup-org-5")
    user = make_user(db, org, email="user@cleanup5.com")

    pr1 = make_purchase_request(db, org.id, user.id, request_number="PR-00001")
    pr2 = make_purchase_request(db, org.id, user.id, request_number="PR-00002")
    pr3 = make_purchase_request(
        db, org.id, user.id, request_number="PR-00003"
    )  # recent, keep

    pr1_id, pr2_id, pr3_id = pr1.id, pr2.id, pr3.id

    backdate(db, pr1, days=40)
    backdate(db, pr2, days=31)
    # pr3 stays recent

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()

    assert not exists(db, pr1_id)
    assert not exists(db, pr2_id)
    assert exists(db, pr3_id)


def test_no_error_when_nothing_to_delete(db: Session):
    """
    If there are no stale drafts, cleanup should run without errors.
    """
    org = make_org(db, name="Cleanup Org 6", subdomain="cleanup-org-6")
    make_user(db, org, email="user@cleanup6.com")
    db.flush()

    with patch("app.jobs.cleanup.SessionLocal", return_value=db):
        scheduled_cleanup()  # Should not raise
