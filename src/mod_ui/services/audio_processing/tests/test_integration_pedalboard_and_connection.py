import asyncio
import os
import uuid

import pytest
from servicebus import Service

from mod_ui.services.audio_processing import main as audio_main


@pytest.mark.asyncio
async def test_pedalboard_create_save_load_and_connection(tmp_path):
    # Ensure modhost runs in simulate mode for tests
    os.environ["SIMULATE_MODHOST"] = "true"

    # Start the audio processing service
    await audio_main.startup()

    # give the service time to bind sockets
    await asyncio.sleep(0.1)

    client = Service(f"client_{uuid.uuid4().hex[:8]}")
    await client.start()

    try:
        # Create a pedalboard
        resp = await client.call(
            "audio_processing", "create_pedalboard", name="Integration PB"
        )
        # Some handlers return dict with status, others return pedalboard id directly
        assert resp is not None

        # Save current pedalboard
        saved = await client.call("audio_processing", "save_pedalboard")
        assert saved.get("status") == "ok"

        # Get current pedalboard
        current = await client.call("audio_processing", "get_current_pedalboard")
        assert current.get("pedalboard") is not None

        # Load a plugin if available
        avail = await client.call("audio_processing", "get_available_plugins")
        if avail and isinstance(avail, dict) and len(list(avail.keys())) > 0:
            test_uri = list(avail.keys())[0]
            load_res = await client.call(
                "audio_processing", "load_plugin", uri=test_uri
            )
            assert load_res.get("instance_id") is not None

        # Try creating a connection if there are at least two instances
        current_pb = current["pedalboard"]
        instances = []
        for p in current_pb.get("plugins", []):
            instances.append(p.get("instance_id") or p.get("id") or p.get("instance"))

        if len(instances) >= 2:
            src = instances[0]
            tgt = instances[1]
            conn = await client.call(
                "audio_processing",
                "create_connection",
                source_plugin=src,
                source_port="out",
                target_plugin=tgt,
                target_port="in",
            )
            assert "connection_id" in conn

    finally:
        await client.stop()
        await audio_main.shutdown()
