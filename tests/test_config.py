from app.core.config import settings


def test_api_base_property():
    assert settings.API_BASE == f"{settings.API_PREFIX}/{settings.API_VERSION}"
