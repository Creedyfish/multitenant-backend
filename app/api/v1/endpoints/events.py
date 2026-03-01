"""
app/routers/events.py

SSE endpoint — clients connect here to receive real-time events for their org.

How it works:
1. Client connects to GET /events with their auth token + tenant header
2. Server subscribes to Redis channel sse:events:{org_id}
3. Any event published to that channel is streamed to the client instantly
4. Connection stays open until client disconnects

Testing in terminal:
    curl -N -H "Authorization: Bearer <token>" \
         -H "x-tenant-id: <subdomain>" \
         http://localhost:8000/api/v1/events
"""

import asyncio
import json
import uuid
from typing import Annotated, AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_active_user
from app.core.redis import redis_client
from app.middleware.tenant import OrgID
from app.models.user import User
from app.services.event_publisher import get_channel

logger = structlog.get_logger()


router = APIRouter()


async def event_stream(
    org_id: uuid.UUID,
    request: Request,
) -> AsyncGenerator[str, None]:
    """
    Subscribes to the org's Redis channel and yields SSE-formatted messages.
    Runs in a thread to avoid blocking the async event loop.
    """
    channel = get_channel(org_id)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)
    logger.info("SSE client connected", org_id=str(org_id))

    try:
        # Send an initial ping so the client knows the connection is live
        yield "event: ping\ndata: connected\n\n"

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("SSE client disconnected", org_id=str(org_id))
                break

            # get_message is non-blocking — returns None if nothing waiting
            message = await asyncio.to_thread(
                pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0
            )

            if message and message["type"] == "message":
                raw = message["data"]
                try:
                    parsed = json.loads(raw)
                    event_type = parsed.get("type", "message")
                    data = json.dumps(parsed.get("data", {}))
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Malformed event payload", raw=raw)

            # Small sleep to avoid a tight loop burning CPU
            await asyncio.sleep(0.1)

    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        logger.info("SSE subscription closed", org_id=str(org_id))


@router.get("")
async def sse_events(
    request: Request,
    org_id: OrgID,
    _current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Connect to this endpoint to receive real-time events for your org.

    Events:
    - ping         — sent on connect to confirm connection is live
    - low_stock    — fired when a product drops below min_stock_level
    - stock_movement — fired after any stock in/out/transfer/adjust
    """
    return StreamingResponse(
        event_stream(org_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disables Nginx buffering for SSE
        },
    )
