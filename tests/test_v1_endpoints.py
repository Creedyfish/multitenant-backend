import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import router
from app.core.config import settings


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix=settings.API_BASE)
    return TestClient(app)


def test_v1_auth_token_endpoint():
    client = create_test_client()
    response = client.post(
        f"{settings.API_BASE}/auth/token",
        data={"username": "demo"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert response.json() == {"access_token": "demo", "token_type": "bearer"}


def test_v1_items_endpoint():
    client = create_test_client()
    response = client.get(f"{settings.API_BASE}/items/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello world Items"}


def test_v1_users_me_endpoint():
    client = create_test_client()
    token = jwt.encode(
        {"sub": "johndoe"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    response = client.get(
        f"{settings.API_BASE}/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "johndoe"
