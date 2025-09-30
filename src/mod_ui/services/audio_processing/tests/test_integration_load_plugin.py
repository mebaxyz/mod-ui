import asyncio
import os
import uuid

import pytest
from servicebus import Service

from mod_ui.services.audio_processing import main as audio_processing_main

# Ensure mod-host runs in simulate mode for tests
os.environ["SIMULATE_MODHOST"] = "true"


@pytest.mark.asyncio
async def test_load_plugin_rpc_and_event():
    # Start the audio_processing service in-process
    await audio_processing_main.startup()

    # Give ZeroMQ sockets a moment to bind
    await asyncio.sleep(0.15)

    client = Service(f"client_{uuid.uuid4().hex[:8]}")
    await client.start()

    # Subscriber to listen for plugin_loaded events
    sub = Service(f"sub_{uuid.uuid4().hex[:8]}")
    await sub.start()

    # Ensure subscription is ready
    await asyncio.sleep(0.05)

    got = asyncio.Event()
    payload = {}

    async def on_plugin_loaded(event):
        payload["instance_id"] = event.data.get("instance_id")
        payload["uri"] = event.data.get("uri")
        got.set()

    sub.register_event_handler("plugin_loaded", on_plugin_loaded)

    # Give subscription a moment
    await asyncio.sleep(0.05)

    # Call load_plugin RPC (use one available plugin URI)
    plugins = await client.call("audio_processing", "get_available_plugins")
    # get_available_plugins returns dict of plugins
    test_uri = list(plugins.keys())[0]

    # Make RPC to load plugin
    result = await asyncio.wait_for(
        client.call("audio_processing", "load_plugin", uri=test_uri, x=10, y=20),
        timeout=5.0,
    )

    assert "instance_id" in result

    # Wait for plugin_loaded event
    await asyncio.wait_for(got.wait(), timeout=2.0)

    assert payload.get("uri") == test_uri
    assert payload.get("instance_id") is not None

    # Cleanup
    await client.stop()
    await sub.stop()
    await audio_processing_main.shutdown()
