import os

import jwt


def test_login_invalid_credentials(app_client):
    response = app_client.post(
        "/token",
        data={"username": "johndoe", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Credentials"


def test_users_me_with_token(app_client):
    secret = os.environ.get("SECRET_KEY", "testsecret")
    token = jwt.encode({"sub": "johndoe"}, secret, algorithm="HS256")

    response = app_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "johndoe"
    assert data["email"] == "johndoe@example.com"


def test_settings_endpoint(app_client):
    response = app_client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["API_PREFIX"] == "/api"
    assert data["API_VERSION"] == "v1"
