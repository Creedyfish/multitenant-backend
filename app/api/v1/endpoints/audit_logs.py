import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_active_user
from app.db.database import DB
from app.middleware.tenant import OrgID
from app.models.user import User
from app.schemas.audit_log import AuditLogOut
from app.services.audit_log import AuditService

router = APIRouter()


def get_service(db: DB) -> AuditService:
    return AuditService(db)


@router.get("/", response_model=list[AuditLogOut])
def list_audit_logs(
    _: Annotated[User, Depends(get_current_active_user)],
    org_id: OrgID,
    service: AuditService = Depends(get_service),
    entity: str | None = Query(None, description="e.g. Product, PurchaseRequest"),
    entity_id: str | None = Query(None),
    actor_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None, description="e.g. CREATE, UPDATE, APPROVE"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return service.get_all(
        org_id=org_id,
        entity=entity,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/{audit_id}", response_model=AuditLogOut)
def get_audit_log(
    audit_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_active_user)],
    org_id: OrgID,
    service: AuditService = Depends(get_service),
):
    return service.get_by_id(org_id=org_id, audit_id=audit_id)
