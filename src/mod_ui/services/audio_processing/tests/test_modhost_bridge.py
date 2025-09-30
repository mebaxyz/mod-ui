"""
Tests for ModHostBridge component.
"""

import os
from unittest.mock import patch

import pytest

from mod_ui.services.audio_processing.modhost_bridge import ModHostBridge


class TestModHostBridge:
    """Test cases for ModHostBridge."""

    @pytest.mark.asyncio
    async def test_simulation_mode_initialization(self):
        """Test that bridge initializes correctly in simulation mode."""
        with patch.dict(os.environ, {"SIMULATE_MODHOST": "true"}):
            bridge = ModHostBridge()
            assert bridge.simulate is True
            assert bridge.process is None

    @pytest.mark.asyncio
    async def test_start_simulation_mode(self):
        """Test starting bridge in simulation mode."""
        with patch.dict(os.environ, {"SIMULATE_MODHOST": "true"}):
            bridge = ModHostBridge()
            result = await bridge.start()
            assert result is True
            assert bridge._connected is True

    @pytest.mark.asyncio
    async def test_stop_simulation_mode(self):
        """Test stopping bridge in simulation mode."""
        with patch.dict(os.environ, {"SIMULATE_MODHOST": "true"}):
            bridge = ModHostBridge()
            await bridge.start()
            await bridge.stop()
            assert bridge._connected is False

    @pytest.mark.asyncio
    async def test_ping_simulation_mode(self):
        """Test ping in simulation mode."""
        with patch.dict(os.environ, {"SIMULATE_MODHOST": "true"}):
            bridge = ModHostBridge()
            await bridge.start()

            result = await bridge.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_ping_not_connected(self):
        """Test ping when not connected."""
        bridge = ModHostBridge()
        result = await bridge.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_add_plugin_simulation(self, modhost_bridge):
        """Test adding plugin in simulation mode."""
        result = await modhost_bridge.add_plugin("http://example.com/plugin", "test_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_plugin_simulation(self, modhost_bridge):
        """Test removing plugin in simulation mode."""
        # First add a plugin
        await modhost_bridge.add_plugin("http://example.com/plugin", "test_1")

        # Then remove it
        result = await modhost_bridge.remove_plugin("test_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_set_parameter_simulation(self, modhost_bridge):
        """Test setting parameter in simulation mode."""
        result = await modhost_bridge.set_parameter("test_1", "gain", 0.5)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_parameter_simulation(self, modhost_bridge):
        """Test getting parameter in simulation mode."""
        # In simulation mode, get_parameter returns a simulated value (0.5)
        result = await modhost_bridge.get_parameter("test_1", "gain")
        assert result == 0.5

    @pytest.mark.asyncio
    async def test_connect_ports_simulation(self, modhost_bridge):
        """Test connecting ports in simulation mode."""
        result = await modhost_bridge.connect_ports("system:capture_1", "effect_1:in")
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_ports_simulation(self, modhost_bridge):
        """Test disconnecting ports in simulation mode."""
        # First connect ports
        await modhost_bridge.connect_ports("system:capture_1", "effect_1:in")

        # Then disconnect
        result = await modhost_bridge.disconnect_ports(
            "system:capture_1", "effect_1:in"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_real_mode_initialization(self):
        """Test initialization in real mode (without simulation)."""
        with patch.dict(os.environ, {}, clear=True):
            bridge = ModHostBridge()
            assert bridge.simulate is False
