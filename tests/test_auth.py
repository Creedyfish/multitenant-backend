"""
Auth tests.

Covers:
- Successful login returns access token
- Wrong password → 401
- Wrong subdomain (user exists in org-a, tries to log in via org-b) → 401
- Missing tenant header → 400
- Accessing a protected route without a token → 401
- Accessing a protected route with a malformed/garbage token → 401
- /auth/refresh with no cookie → 401
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import RoleEnum
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import make_org, make_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def org(db: Session):
    return make_org(db, name="Auth Org", subdomain="auth-org")


@pytest.fixture()
def user(db: Session, org: Organization):
    return make_user(db, org, email="auth@example.com", role=RoleEnum.ADMIN)


# ── Login ─────────────────────────────────────────────────────────────────────


class TestLogin:
    def test_valid_login_returns_token(self, client: TestClient, user: User):
        response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "testpassword"},
            headers={"x-tenant-id": "auth-org"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client: TestClient, user: User):
        response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "wrongpassword"},
            headers={"x-tenant-id": "auth-org"},
        )
        assert response.status_code == 401

    def test_nonexistent_user_returns_401(self, client: TestClient, org: Organization):
        response = client.post(
            "/auth/token",
            data={"username": "nobody@example.com", "password": "testpassword"},
            headers={"x-tenant-id": "auth-org"},
        )
        assert response.status_code == 401

    def test_wrong_subdomain_returns_401(
        self, client: TestClient, user: User, db: Session
    ):
        """User exists in auth-org but tries to log in via other-org."""
        make_org(db, name="Other Org", subdomain="other-org")
        response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "testpassword"},
            headers={"x-tenant-id": "other-org"},
        )
        assert response.status_code == 401

    def test_missing_tenant_header_returns_400(self, client: TestClient, user: User):
        response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "testpassword"},
        )
        assert response.status_code == 400


# ── Protected route access ────────────────────────────────────────────────────


class TestProtectedRoutes:
    def test_no_token_returns_401(self, client: TestClient):
        response = client.get("/products/")
        assert response.status_code == 401

    def test_garbage_token_returns_401(self, client: TestClient):
        response = client.get(
            "/products/",
            headers={"Authorization": "Bearer this.is.not.a.real.token"},
        )
        assert response.status_code == 401

    def test_malformed_auth_header_returns_401(self, client: TestClient):
        """Missing 'Bearer' prefix."""
        response = client.get(
            "/products/",
            headers={"Authorization": "justthetoken"},
        )
        assert response.status_code == 401


# ── Refresh token ─────────────────────────────────────────────────────────────


class TestRefreshToken:
    def test_refresh_without_cookie_returns_401(self, client: TestClient):
        response = client.post("/auth/refresh")
        assert response.status_code == 401

    def test_valid_login_sets_refresh_cookie(self, client: TestClient, user: User):
        response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "testpassword"},
            headers={"x-tenant-id": "auth-org"},
        )
        assert response.status_code == 200
        assert "refresh_token" in response.cookies

    def test_refresh_with_valid_cookie_returns_new_access_token(
        self, client: TestClient, user: User
    ):
        # Login to get the cookie
        login_response = client.post(
            "/auth/token",
            data={"username": "auth@example.com", "password": "testpassword"},
            headers={"x-tenant-id": "auth-org"},
        )
        assert login_response.status_code == 200

        # The TestClient carries cookies automatically between requests
        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()
