import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.database import DB
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


class AuditService:
    def __init__(self, db: DB):
        self.db = db

    # ── Internal logging (called by other services) ───────────────────────────

    def log(self, org_id: uuid.UUID, payload: AuditLogCreate) -> AuditLog:
        entry = AuditLog(
            org_id=org_id,
            actor_id=payload.actor_id,
            action=payload.action,
            entity=payload.entity,
            entity_id=payload.entity_id,
            before=payload.before,
            after=payload.after,
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
        )
        self.db.add(entry)
        self.db.flush()  # write within the caller's transaction, no commit here
        return entry

    # ── Query methods ─────────────────────────────────────────────────────────

    def get_all(
        self,
        org_id: uuid.UUID,
        entity: str | None = None,
        entity_id: str | None = None,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AuditLog]:
        q = select(AuditLog).where(AuditLog.org_id == org_id)

        if entity:
            q = q.where(AuditLog.entity == entity)
        if entity_id:
            q = q.where(AuditLog.entity_id == entity_id)
        if actor_id:
            q = q.where(AuditLog.actor_id == actor_id)
        if action:
            q = q.where(AuditLog.action == action)
        if start_date:
            q = q.where(AuditLog.timestamp >= start_date)
        if end_date:
            q = q.where(AuditLog.timestamp <= end_date)

        q = q.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
        return list(self.db.execute(q).scalars().all())

    def get_by_id(self, org_id: uuid.UUID, audit_id: uuid.UUID) -> AuditLog:
        from fastapi import HTTPException

        entry = self.db.execute(
            select(AuditLog).where(
                AuditLog.id == audit_id,
                AuditLog.org_id == org_id,
            )
        ).scalar_one_or_none()

        if entry is None:
            raise HTTPException(status_code=404, detail="Audit log not found.")
        return entry
