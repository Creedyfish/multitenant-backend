from app.crud.user import get_user


def test_get_user_found():
    db = {
        "alice": {
            "username": "alice",
            "full_name": "Alice",
            "email": "alice@example.com",
            "hashed_password": "hashed",
            "disabled": False,
        }
    }
    user = get_user(db, "alice")
    assert user is not None
    assert user.username == "alice"


def test_get_user_not_found():
    user = get_user({}, "missing")
    assert user is None
