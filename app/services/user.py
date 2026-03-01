import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.security import get_password_hash, verify_password
from app.db.database import DB
from app.models import RoleEnum, User
from app.models.organization import Organization
from app.schemas.audit_log import AuditLogCreate
from app.schemas.user import RegisterRequest, UserCreate, UserUpdate, UserUpdatePassword
from app.services.audit_log import AuditService


class UserService:
    def __init__(self, db: DB):
        self.db = db
        self.audit = AuditService(db)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_or_404(self, user_id: uuid.UUID, org_id: uuid.UUID) -> User:
        user = self.db.execute(
            select(User).where(User.id == user_id, User.org_id == org_id)
        ).scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    def _assert_email_unique(self, email: str, org_id: uuid.UUID) -> None:
        existing = self.db.execute(
            select(User).where(User.email == email, User.org_id == org_id)
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="A user with this email already exists in this organization.",
            )

    # ── Auth helpers (kept from original get_user) ────────────────────────────

    def get_by_email(self, email: str, subdomain: str | None = None) -> User | None:
        query = (
            select(User)
            .options(joinedload(User.organization))
            .join(User.organization)
            .where(User.email == email)
        )
        if subdomain:
            query = query.where(Organization.subdomain == subdomain)
        return self.db.execute(query).scalar_one_or_none()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, payload: RegisterRequest) -> User:
        """Create an org and its first admin user in a single transaction."""
        # Check subdomain availability
        existing_org = self.db.execute(
            select(Organization).where(Organization.subdomain == payload.subdomain)
        ).scalar_one_or_none()

        if existing_org:
            raise HTTPException(
                status_code=409,
                detail=f"Subdomain '{payload.subdomain}' is already taken.",
            )

        # Check email uniqueness within the new org isn't needed yet
        # (org doesn't exist), but check globally if you want unique emails
        org = Organization(name=payload.org_name, subdomain=payload.subdomain)
        self.db.add(org)
        self.db.flush()  # get org.id

        user = User(
            org_id=org.id,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=get_password_hash(payload.password),
            role=RoleEnum.ADMIN,  # first user is always admin
        )
        self.db.add(user)
        self.db.flush()  # get user.id

        self.audit.log(
            org.id,
            AuditLogCreate(
                actor_id=user.id,
                action="REGISTER",
                entity="User",
                entity_id=str(user.id),
                before=None,
                after={
                    "email": user.email,
                    "role": RoleEnum.ADMIN.value,
                    "org_id": str(org.id),
                    "subdomain": org.subdomain,
                },
            ),
        )

        self.db.commit()
        self.db.refresh(user)
        return user

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get_all(self, org_id: uuid.UUID) -> list[User]:
        return list(
            self.db.execute(
                select(User).where(User.org_id == org_id).order_by(User.created_at)
            )
            .scalars()
            .all()
        )

    def get_by_id(self, org_id: uuid.UUID, user_id: uuid.UUID) -> User:
        return self._get_or_404(user_id, org_id)

    def create(
        self,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: UserCreate,
    ) -> User:
        self._assert_email_unique(payload.email, org_id)

        user = User(
            org_id=org_id,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=get_password_hash(payload.password),
            role=payload.role,
        )
        self.db.add(user)
        self.db.flush()

        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="CREATE",
                entity="User",
                entity_id=str(user.id),
                before=None,
                after={"email": user.email, "role": user.role.value},
            ),
        )

        self.db.commit()
        self.db.refresh(user)
        return user

    def update(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: UserUpdate,
    ) -> User:
        user = self._get_or_404(user_id, org_id)
        before = {"email": user.email, "role": user.role.value}

        if payload.email and payload.email != user.email:
            self._assert_email_unique(payload.email, org_id)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="UPDATE",
                entity="User",
                entity_id=str(user.id),
                before=before,
                after={"email": user.email, "role": user.role.value},
            ),
        )

        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: UserUpdatePassword,
    ) -> User:
        user = self._get_or_404(user_id, org_id)

        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(
                status_code=400, detail="Current password is incorrect."
            )

        user.password_hash = get_password_hash(payload.new_password)

        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=user_id,
                action="CHANGE_PASSWORD",
                entity="User",
                entity_id=str(user.id),
                before=None,
                after={"password_changed": True},
            ),
        )

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        user = self._get_or_404(user_id, org_id)

        # Prevent deleting yourself
        if user_id == actor_id:
            raise HTTPException(
                status_code=400, detail="You cannot delete your own account."
            )

        self.audit.log(
            org_id,
            AuditLogCreate(
                actor_id=actor_id,
                action="DELETE",
                entity="User",
                entity_id=str(user.id),
                before={"email": user.email, "role": user.role.value},
                after={"deleted": True},
            ),
        )

        self.db.delete(user)
        self.db.commit()
