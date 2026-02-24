import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.models.enums import PurchaseRequestStatusEnum
from app.models.user import User
from app.schemas.purchase_request import (
    PurchaseRequestCreate,
    PurchaseRequestListOut,
    PurchaseRequestOut,
    PurchaseRequestReject,
    PurchaseRequestUpdate,
)
from app.services.purchase_request import PurchaseRequestService

router = APIRouter()


def get_service(db: DB) -> PurchaseRequestService:
    return PurchaseRequestService(db)


@router.post("/", response_model=PurchaseRequestOut, status_code=201)
def create_purchase_request(
    payload: PurchaseRequestCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.create(
        org_id=current_user.org_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("/", response_model=list[PurchaseRequestListOut])
def list_purchase_requests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    status: PurchaseRequestStatusEnum | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: PurchaseRequestService = Depends(get_service),
):
    return service.get_all(
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_role=current_user.role,
        status_filter=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=PurchaseRequestOut)
def get_purchase_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.get_by_id(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.patch("/{request_id}", response_model=PurchaseRequestOut)
def update_purchase_request(
    request_id: uuid.UUID,
    payload: PurchaseRequestUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.update(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
        payload=payload,
    )


@router.post("/{request_id}/submit", response_model=PurchaseRequestOut)
def submit_purchase_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.submit(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.post("/{request_id}/approve", response_model=PurchaseRequestOut)
def approve_purchase_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.approve(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.post("/{request_id}/reject", response_model=PurchaseRequestOut)
def reject_purchase_request(
    request_id: uuid.UUID,
    body: PurchaseRequestReject,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.reject(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
        rejection_reason=body.rejection_reason,
    )


@router.post("/{request_id}/mark-ordered", response_model=PurchaseRequestOut)
def mark_ordered(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PurchaseRequestService = Depends(get_service),
):
    return service.mark_ordered(
        org_id=current_user.org_id,
        request_id=request_id,
        user_id=current_user.id,
        user_role=current_user.role,
    )
