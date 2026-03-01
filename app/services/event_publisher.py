"""
app/services/event_publisher.py

Publishes SSE events to a per-org Redis channel.

Each org gets its own channel: sse:events:{org_id}
The SSE endpoint subscribes to this channel and streams events to connected clients.

Usage:
    publish_event(redis_client, org_id, "low_stock", {
        "product_name": "Widget",
        "current_stock": 3,
        "minimum_stock": 10,
        "warehouse_name": "Main Warehouse",
    })
"""

import json
import uuid

import structlog
from redis import Redis

logger = structlog.get_logger()


def get_channel(org_id: uuid.UUID) -> str:
    """Returns the Redis channel name for an org."""
    return f"sse:events:{org_id}"


def publish_event(
    redis_client: Redis,  # type: ignore
    org_id: uuid.UUID,
    event_type: str,
    data: dict[str, str | int],
) -> None:
    """
    Publish an event to the org's Redis channel.

    event_type examples: "low_stock", "stock_movement", "purchase_request_update"
    data: any JSON-serializable dict with event details
    """
    channel = get_channel(org_id)
    payload = json.dumps({"type": event_type, "data": data})
    try:
        redis_client.publish(channel, payload)
        logger.info("Event published", org_id=str(org_id), type=event_type)
    except Exception as e:
        logger.error(
            "Failed to publish event", org_id=str(org_id), type=event_type, error=str(e)
        )
