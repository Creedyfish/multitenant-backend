import os
from typing import Generator

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.security import get_password_hash
from app.db.database import get_db
from app.main import app
from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.user import User

load_dotenv()

# ── Test database ─────────────────────────────────────────────────────────────

SQLALCHEMY_TEST_DATABASE_URL = os.getenv("DATABASE_URL_TESTING")
if SQLALCHEMY_TEST_DATABASE_URL is None:
    raise RuntimeError(
        "DATABASE_URL_TESTING environment variable must be set for tests."
    )

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Alembic migrations ────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(SQLALCHEMY_TEST_DATABASE_URL))

    # Force clean schema to handle leftover enum types from previous runs
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()

    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")


# ── DB session ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Yields a test DB session wrapped in a transaction that rolls back
    after each test — so each test starts with a clean slate.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """TestClient with get_db overridden to use test session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass  # Rollback handled by db fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://testserver/api/v1") as c:
        yield c
    app.dependency_overrides.clear()


# ── Org + user helpers ────────────────────────────────────────────────────────


def make_org(db: Session, name: str, subdomain: str) -> Organization:
    org = Organization(
        name=name,
        subdomain=subdomain,
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


def make_user(
    db: Session,
    org: Organization,
    email: str,
    role: RoleEnum = RoleEnum.STAFF,
    password: str = "testpassword",
) -> User:
    user = User(
        org_id=org.id,
        email=email,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


# ── Tenant fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def org_a(db: Session) -> Organization:
    return make_org(db, name="Org A", subdomain="org-a")


@pytest.fixture()
def org_b(db: Session) -> Organization:
    return make_org(db, name="Org B", subdomain="org-b")


@pytest.fixture()
def user_a(db: Session, org_a: Organization) -> User:
    return make_user(db, org_a, email="user@orga.com", role=RoleEnum.ADMIN)


@pytest.fixture()
def user_b(db: Session, org_b: Organization) -> User:
    return make_user(db, org_b, email="user@orgb.com", role=RoleEnum.ADMIN)


# ── Auth token helper ─────────────────────────────────────────────────────────


def get_auth_headers(
    client: TestClient, email: str, password: str, subdomain: str
) -> dict[str, str]:
    response = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"x-tenant-id": subdomain},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
