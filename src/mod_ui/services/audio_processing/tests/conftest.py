"""
Test configuration and fixtures for audio processing service tests.
"""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from mod_ui.services.audio_processing.modhost_bridge import ModHostBridge
from mod_ui.services.audio_processing.plugin_manager import PluginManager
from mod_ui.services.audio_processing.session_manager import SessionManager

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_servicebus():
    """Mock servicebus for testing."""
    mock = Mock()
    mock.publish = AsyncMock()
    mock.call = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def modhost_bridge():
    """Create ModHostBridge instance for testing.

    By default tests use a simulated mod-host. To run tests against a real
    mod-host (for integration testing), set the environment variable
    TEST_USE_SIMULATED_MODHOST=false before running pytest. The fixture will
    then attempt to connect to a real mod-host listening on
    MOD_HOST_PORT (default 5555).
    """
    use_sim = os.getenv("TEST_USE_SIMULATED_MODHOST", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    if use_sim:
        # Force simulation mode for tests
        with patch.dict(os.environ, {"SIMULATE_MODHOST": "true"}):
            bridge = ModHostBridge()
            await bridge.start()
            yield bridge
            await bridge.stop()
    else:
        # Use a real mod-host (do not patch SIMULATE_MODHOST)
        bridge = ModHostBridge()
        # ensure simulate flag is False
        bridge.simulate = False
        started = await bridge.start()
        if not started:
            # If we can't start/connect to the real mod-host, skip the test run
            # to avoid failing the whole suite. Individual tests may also skip
            # as appropriate.
            pytest.skip("Could not start/connect to real mod-host; skipping")
        try:
            yield bridge
        finally:
            await bridge.stop()


@pytest_asyncio.fixture
async def plugin_manager(mock_servicebus, modhost_bridge):
    """Create PluginManager instance for testing."""
    manager = PluginManager(modhost_bridge, mock_servicebus)
    await manager.initialize()
    return manager


@pytest.fixture
def session_manager(mock_servicebus, plugin_manager):
    """Create SessionManager instance for testing."""
    return SessionManager(mock_servicebus, plugin_manager)


@pytest.fixture
def sample_plugin_info():
    """Sample plugin information for testing."""
    return {
        "uri": "http://example.com/plugins/reverb",
        "name": "Test Reverb",
        "brand": "Test Audio",
        "version": "1.0.0",
        "license": "GPL",
        "comment": "A test reverb plugin",
        "ports": {
            "audio": {
                "input": [{"index": 0, "name": "Audio In", "symbol": "in"}],
                "output": [{"index": 1, "name": "Audio Out", "symbol": "out"}],
            },
            "control": [
                {
                    "index": 2,
                    "name": "Room Size",
                    "symbol": "room_size",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0,
                }
            ],
        },
    }


@pytest.fixture
def sample_pedalboard():
    """Sample pedalboard data for testing."""
    return {
        "title": "Test Pedalboard",
        "width": 3840,
        "height": 2160,
        "plugins": [
            {
                "instance": 1,
                "uri": "http://example.com/plugins/reverb",
                "x": 100,
                "y": 100,
                "ports": {"room_size": 0.7},
            }
        ],
        "connections": [
            {"source": "system:capture_1", "target": "effect_1:in"},
            {"source": "effect_1:out", "target": "system:playback_1"},
        ],
    }
