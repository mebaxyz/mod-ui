"""
Tests for PluginManager component.
"""

from unittest.mock import AsyncMock

import pytest


class TestPluginManager:
    """Test cases for PluginManager."""

    @pytest.mark.asyncio
    async def test_get_available_plugins(self, plugin_manager):
        """Test getting available plugins."""
        plugins = await plugin_manager.get_available_plugins()
        assert isinstance(plugins, dict)
        # Should have at least the mock plugin
        assert len(plugins) > 0

    @pytest.mark.asyncio
    async def test_load_plugin_success(self, plugin_manager):
        """Test successful plugin loading."""
        # Use the mock plugin URI from available plugins
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        # Mock modhost operations
        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)

        result = await plugin_manager.load_plugin(test_uri, 100, 200)

        assert result is not None
        assert "instance_id" in result
        assert "plugin" in result
        instance_id = result["instance_id"]
        assert instance_id in plugin_manager.instances

    @pytest.mark.asyncio
    async def test_load_plugin_not_found(self, plugin_manager):
        """Test loading non-existent plugin."""
        with pytest.raises(ValueError, match="Plugin not found"):
            await plugin_manager.load_plugin("http://nonexistent.plugin", 0, 0)

    @pytest.mark.asyncio
    async def test_unload_plugin_success(self, plugin_manager):
        """Test successful plugin unloading."""
        # First load a plugin
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)
        plugin_manager.modhost.remove_plugin = AsyncMock(return_value=True)

        load_result = await plugin_manager.load_plugin(test_uri, 100, 200)
        instance_id = load_result["instance_id"]

        # Then unload it
        result = await plugin_manager.unload_plugin(instance_id)

        assert result["status"] == "ok"
        assert instance_id not in plugin_manager.instances

    @pytest.mark.asyncio
    async def test_unload_plugin_not_loaded(self, plugin_manager):
        """Test unloading plugin that isn't loaded."""
        with pytest.raises(ValueError, match="Plugin instance not found"):
            await plugin_manager.unload_plugin("nonexistent_id")

    @pytest.mark.asyncio
    async def test_set_parameter_success(self, plugin_manager):
        """Test successful parameter setting."""
        # Load plugin first
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)
        plugin_manager.modhost.set_parameter = AsyncMock(return_value=True)

        load_result = await plugin_manager.load_plugin(test_uri, 100, 200)
        instance_id = load_result["instance_id"]

        result = await plugin_manager.set_parameter(instance_id, "gain", 0.8)

        assert result["status"] == "ok"
        assert result["value"] == 0.8

        # Check if event was published
        plugin_manager.service_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_set_parameter_plugin_not_loaded(self, plugin_manager):
        """Test setting parameter on non-loaded plugin."""
        with pytest.raises(ValueError, match="Plugin instance not found"):
            await plugin_manager.set_parameter("nonexistent_id", "gain", 0.5)

    @pytest.mark.asyncio
    async def test_get_parameter_success(self, plugin_manager):
        """Test successful parameter getting."""
        # Load plugin first
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)
        plugin_manager.modhost.get_parameter = AsyncMock(return_value=0.6)

        load_result = await plugin_manager.load_plugin(test_uri, 100, 200)
        instance_id = load_result["instance_id"]

        result = await plugin_manager.get_parameter(instance_id, "gain")
        assert result["value"] == 0.6

    @pytest.mark.asyncio
    async def test_get_parameter_plugin_not_loaded(self, plugin_manager):
        """Test getting parameter from non-loaded plugin."""
        with pytest.raises(ValueError, match="Plugin instance not found"):
            await plugin_manager.get_parameter("nonexistent_id", "gain")

    @pytest.mark.asyncio
    async def test_get_plugin_info(self, plugin_manager):
        """Test getting plugin info."""
        # Load plugin first
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)

        load_result = await plugin_manager.load_plugin(test_uri, 100, 200)
        instance_id = load_result["instance_id"]

        result = await plugin_manager.get_plugin_info(instance_id)
        assert "plugin" in result
        assert result["plugin"]["uri"] == test_uri

    @pytest.mark.asyncio
    async def test_list_instances(self, plugin_manager):
        """Test listing plugin instances."""
        # Load multiple plugins
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)

        load_result1 = await plugin_manager.load_plugin(test_uri, 100, 200)
        load_result2 = await plugin_manager.load_plugin(test_uri, 300, 400)

        result = await plugin_manager.list_instances()

        assert "instances" in result
        assert len(result["instances"]) == 2

        instance_ids = [load_result1["instance_id"], load_result2["instance_id"]]
        for instance_id in instance_ids:
            assert instance_id in result["instances"]

    @pytest.mark.asyncio
    async def test_clear_all_plugins(self, plugin_manager):
        """Test clearing all plugins."""
        # Load multiple plugins
        plugins = await plugin_manager.get_available_plugins()
        test_uri = list(plugins.keys())[0]

        plugin_manager.modhost.add_plugin = AsyncMock(return_value=True)
        plugin_manager.modhost.remove_plugin = AsyncMock(return_value=True)

        await plugin_manager.load_plugin(test_uri, 100, 200)
        await plugin_manager.load_plugin(test_uri, 300, 400)

        await plugin_manager.clear_all()

        assert len(plugin_manager.instances) == 0
