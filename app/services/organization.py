import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.database import DB
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    def __init__(self, db: DB):
        self.db = db

    def get_by_id(self, org_id: uuid.UUID) -> Organization:
        org = self.db.execute(
            select(Organization).where(Organization.id == org_id)
        ).scalar_one_or_none()

        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        return org

    def get_by_subdomain(self, subdomain: str) -> Organization:
        org = self.db.execute(
            select(Organization).where(Organization.subdomain == subdomain)
        ).scalar_one_or_none()

        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found.")
        return org

    def create(self, payload: OrganizationCreate) -> Organization:
        existing = self.db.execute(
            select(Organization).where(Organization.subdomain == payload.subdomain)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Subdomain '{payload.subdomain}' is already taken.",
            )

        org = Organization(name=payload.name, subdomain=payload.subdomain)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def update(self, org_id: uuid.UUID, payload: OrganizationUpdate) -> Organization:
        org = self.get_by_id(org_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(org, field, value)

        self.db.commit()
        self.db.refresh(org)
        return org
