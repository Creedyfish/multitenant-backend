from fastapi import HTTPException
from sqlalchemy import select

from app.db import DB
from app.models import Organization


def create_organization(name: str, subdomain: str, db: DB):
    org = db.execute(
        select(Organization).where(Organization.subdomain == subdomain)
    ).scalar_one_or_none()

    if org:
        raise HTTPException(
            status_code=409, detail=f"Subdomain '{subdomain}' already exists"
        )

    data = Organization(name=name, subdomain=subdomain)
    db.add(data)
    db.flush()
    db.refresh(data)
    return data
