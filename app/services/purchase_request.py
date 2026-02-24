import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.database import DB
from app.models.enums import PurchaseRequestStatusEnum, RoleEnum
from app.models.purchase_request import PurchaseRequest, PurchaseRequestItem
from app.schemas.purchase_request import PurchaseRequestCreate, PurchaseRequestUpdate

# ── State machine ─────────────────────────────────────────────────────────────

TRANSITIONS: dict[PurchaseRequestStatusEnum, list[PurchaseRequestStatusEnum]] = {
    PurchaseRequestStatusEnum.DRAFT: [PurchaseRequestStatusEnum.SUBMITTED],
    PurchaseRequestStatusEnum.SUBMITTED: [
        PurchaseRequestStatusEnum.APPROVED,
        PurchaseRequestStatusEnum.REJECTED,
    ],
    PurchaseRequestStatusEnum.APPROVED: [PurchaseRequestStatusEnum.ORDERED],
    PurchaseRequestStatusEnum.REJECTED: [],
    PurchaseRequestStatusEnum.ORDERED: [],
}

MANAGER_ONLY_TRANSITIONS = {
    PurchaseRequestStatusEnum.APPROVED,
    PurchaseRequestStatusEnum.REJECTED,
}


class PurchaseRequestService:
    def __init__(self, db: DB):
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _assert_transition(
        self,
        current: PurchaseRequestStatusEnum,
        target: PurchaseRequestStatusEnum,
        user_role: RoleEnum,
    ) -> None:
        if target not in TRANSITIONS[current]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from {current.value} to {target.value}.",
            )
        if target in MANAGER_ONLY_TRANSITIONS and user_role not in (
            RoleEnum.ADMIN,
            RoleEnum.MANAGER,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers and admins can approve or reject requests.",
            )

    def _get_or_404(self, request_id: uuid.UUID, org_id: uuid.UUID) -> PurchaseRequest:
        pr = self.db.execute(
            select(PurchaseRequest)
            .where(
                PurchaseRequest.id == request_id,
                PurchaseRequest.org_id == org_id,
            )
            .options(selectinload(PurchaseRequest.items))
        ).scalar_one_or_none()

        if pr is None:
            raise HTTPException(status_code=404, detail="Purchase request not found.")
        return pr

    def _next_request_number(self, org_id: uuid.UUID) -> str:
        count = self.db.execute(
            select(func.count(PurchaseRequest.id)).where(
                PurchaseRequest.org_id == org_id
            )
        ).scalar_one()
        return f"PR-{count + 1:05d}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    def _assert_ownership_or_role(
        self, pr: PurchaseRequest, user_id: uuid.UUID, user_role: RoleEnum
    ) -> None:
        """STAFF can only act on their own requests."""
        if user_role == RoleEnum.STAFF and pr.created_by != user_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    # ── Public methods ────────────────────────────────────────────────────────

    def get_all(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
        status_filter: PurchaseRequestStatusEnum | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[PurchaseRequest]:
        q = select(PurchaseRequest).where(PurchaseRequest.org_id == org_id)

        if user_role == RoleEnum.STAFF:
            q = q.where(PurchaseRequest.created_by == user_id)

        if status_filter:
            q = q.where(PurchaseRequest.status == status_filter)

        q = q.order_by(PurchaseRequest.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(q).scalars().all())

    def get_by_id(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_ownership_or_role(pr, user_id, user_role)
        return pr

    def create(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: PurchaseRequestCreate,
    ) -> PurchaseRequest:
        pr = PurchaseRequest(
            org_id=org_id,
            request_number=self._next_request_number(org_id),
            created_by=user_id,
            notes=payload.notes,
        )
        self.db.add(pr)
        self.db.flush()  # populate pr.id before inserting items

        for item_data in payload.items:
            self.db.add(
                PurchaseRequestItem(
                    request_id=pr.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    estimated_price=item_data.estimated_price,
                    supplier_id=item_data.supplier_id,
                )
            )

        self.db.commit()
        self.db.refresh(pr)
        return pr

    def update(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
        payload: PurchaseRequestUpdate,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_ownership_or_role(pr, user_id, user_role)

        if pr.status != PurchaseRequestStatusEnum.DRAFT:
            raise HTTPException(
                status_code=422, detail="Only DRAFT requests can be edited."
            )

        if payload.notes is not None:
            pr.notes = payload.notes

        if payload.items is not None:
            for item in pr.items:
                self.db.delete(item)
            self.db.flush()
            for item_data in payload.items:
                self.db.add(
                    PurchaseRequestItem(
                        request_id=pr.id,
                        product_id=item_data.product_id,
                        quantity=item_data.quantity,
                        estimated_price=item_data.estimated_price,
                        supplier_id=item_data.supplier_id,
                    )
                )

        self.db.commit()
        self.db.refresh(pr)
        return pr

    def submit(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_ownership_or_role(pr, user_id, user_role)
        self._assert_transition(
            pr.status, PurchaseRequestStatusEnum.SUBMITTED, user_role
        )

        pr.status = PurchaseRequestStatusEnum.SUBMITTED
        self.db.commit()
        self.db.refresh(pr)
        return pr

    def approve(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_transition(
            pr.status, PurchaseRequestStatusEnum.APPROVED, user_role
        )

        pr.status = PurchaseRequestStatusEnum.APPROVED
        pr.approved_by = user_id
        pr.approved_at = self._now()
        self.db.commit()
        self.db.refresh(pr)
        return pr

    def reject(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
        rejection_reason: str,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_transition(
            pr.status, PurchaseRequestStatusEnum.REJECTED, user_role
        )

        pr.status = PurchaseRequestStatusEnum.REJECTED
        pr.rejected_by = user_id
        pr.rejected_at = self._now()
        pr.rejection_reason = rejection_reason
        self.db.commit()
        self.db.refresh(pr)
        return pr

    def mark_ordered(
        self,
        org_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: RoleEnum,
    ) -> PurchaseRequest:
        pr = self._get_or_404(request_id, org_id)
        self._assert_transition(pr.status, PurchaseRequestStatusEnum.ORDERED, user_role)

        pr.status = PurchaseRequestStatusEnum.ORDERED
        self.db.commit()
        self.db.refresh(pr)
        return pr
