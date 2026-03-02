import json
from typing import Any
from uuid import UUID

from app.core.redis import redis_client

CACHE_TTL = 300  # 5 minutes


def make_list_key(
    org_id: UUID, search: str | None, category: str | None, limit: int, offset: int
) -> str:
    return f"products:{org_id}:all:{search}:{category}:{limit}:{offset}"


def make_single_key(org_id: UUID, product_id: UUID) -> str:
    return f"products:{org_id}:{product_id}"


def get_cached(key: str) -> dict[str, Any] | None:
    value = redis_client.get(key)
    if value:
        return json.loads(value)  # type: ignore[no-any-return]
    return None


def set_cache(key: str, data: dict[str, Any]) -> None:
    redis_client.setex(key, CACHE_TTL, json.dumps(data))


def invalidate_org_products(org_id: UUID) -> None:
    pattern = f"products:{org_id}:*"
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
