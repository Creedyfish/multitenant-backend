from app.models.items import ItemPayload
from app.schemas.user import User


def test_user_schema_optional_fields():
    user = User(username="jane")
    assert user.email is None
    assert user.full_name is None
    assert user.disabled is None


def test_item_payload_schema():
    payload = ItemPayload(item_id=1, item_name="Widget", quantity=3)
    assert payload.item_id == 1
    assert payload.item_name == "Widget"
    assert payload.quantity == 3
