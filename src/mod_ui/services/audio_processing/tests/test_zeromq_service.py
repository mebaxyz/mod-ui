import asyncio

import pytest
from servicebus import Service

# Import the audio_processing module so tests can start the service in-process
from mod_ui.services.audio_processing import main as audio_processing_main


@pytest.mark.asyncio
async def test_health():
    # Start the audio_processing service in-process
    await audio_processing_main.startup()
    # Give ZeroMQ sockets a moment to bind
    await asyncio.sleep(0.1)

    service = Service("test_client")
    await service.start()
    try:
        result = await asyncio.wait_for(
            service.call("audio_processing", "health"), timeout=5.0
        )
        assert result["service"] == "audio_processing"
        assert result["status"] == "healthy"
        assert result["details"]["service_bus_connected"] is True
    finally:
        await service.stop()
        # Shutdown the in-process service
        await audio_processing_main.shutdown()


@pytest.mark.asyncio
async def test_echo():
    # Start the audio_processing service in-process
    await audio_processing_main.startup()
    # Give ZeroMQ sockets a moment to bind
    await asyncio.sleep(0.1)

    service = Service("test_client")
    await service.start()
    try:
        result = await asyncio.wait_for(
            service.call("audio_processing", "echo", message="Hello MOD UI!"),
            timeout=5.0,
        )
        assert result["echo"] == "Hello MOD UI!"
    finally:
        await service.stop()
        # Shutdown the in-process service
        await audio_processing_main.shutdown()
