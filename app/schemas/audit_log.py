import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    entity: str
    entity_id: str
    before: dict[str, Any] | None
    after: dict[str, Any]
    timestamp: datetime
    ip_address: str | None
    user_agent: str | None


class AuditLogCreate(BaseModel):
    """Used internally by other services to log actions — not a user-facing endpoint."""

    actor_id: uuid.UUID
    action: str
    entity: str
    entity_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any]
    ip_address: str | None = None
    user_agent: str | None = None
