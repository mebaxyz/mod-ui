import asyncio
import uuid

import pytest
from servicebus import Service


@pytest.mark.asyncio
async def test_pubsub_event_delivery():
    # Create unique service names to avoid accidental port collisions
    pub_name = f"pub_{uuid.uuid4().hex[:8]}"
    sub_name = f"sub_{uuid.uuid4().hex[:8]}"

    publisher = Service(pub_name)
    subscriber = Service(sub_name)

    await subscriber.start()
    await publisher.start()

    # Wait briefly to ensure sockets have bound and connected
    await asyncio.sleep(0.15)

    got = asyncio.Event()
    result = {}

    async def handler(event):
        # store minimal info and notify
        result["event_type"] = event.event_type
        result["data"] = event.data
        result["source"] = event.service_name
        got.set()

    # Register event handler on subscriber
    subscriber.register_event_handler("test.event", handler)

    # Give subscription a moment to be applied
    await asyncio.sleep(0.05)

    # Publish an event from publisher
    await publisher.publish_event("test.event", {"hello": "world"})

    # Wait for event to be received
    await asyncio.wait_for(got.wait(), timeout=2.0)

    assert result.get("event_type") == "test.event"
    assert result.get("data") == {"hello": "world"}
    assert result.get("source") == pub_name

    # Clean up
    await publisher.stop()
    await subscriber.stop()
