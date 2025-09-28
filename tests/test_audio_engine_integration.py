"""
Audio Engine Service Integration Test

This test validates the audio engine service can communicate with mod-host
and perform basic plugin operations.
"""

import asyncio
import json
from typing import Any, Dict

import httpx
import pytest

from src.mod_ui.services.audio_engine.models import (
    AddPluginCommand,
    ConnectPortsCommand,
    RemovePluginCommand,
    SetParameterCommand,
    SetTransportCommand,
)
from src.mod_ui.services.audio_engine.service import AudioEngineService


class MockModHost:
    """Mock mod-host for testing without actual audio engine"""

    def __init__(self, write_port=5555, read_port=5556):
        self.write_port = write_port
        self.read_port = read_port
        self.write_server = None
        self.read_server = None
        self.plugins = {}
        self.connections = []
        self.transport = {"rolling": False, "bpm": 120.0, "bpb": 4.0}

    async def start(self):
        """Start mock mod-host servers"""
        self.write_server = await asyncio.start_server(
            self._handle_write_connection, "localhost", self.write_port
        )
        self.read_server = await asyncio.start_server(
            self._handle_read_connection, "localhost", self.read_port
        )
        print(f"Mock mod-host started on ports {self.write_port}/{self.read_port}")

    async def stop(self):
        """Stop mock mod-host servers"""
        if self.write_server:
            self.write_server.close()
            await self.write_server.wait_closed()
        if self.read_server:
            self.read_server.close()
            await self.read_server.wait_closed()

    async def _handle_write_connection(self, reader, writer):
        """Handle write socket connection (commands)"""
        try:
            while True:
                data = await reader.readuntil(b"\0")
                if not data:
                    break

                command = data[:-1].decode("utf-8")
                response = await self._process_command(command)

                writer.write(f"{response}\0".encode("utf-8"))
                await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Write connection error: {e}")
        finally:
            writer.close()

    async def _handle_read_connection(self, reader, writer):
        """Handle read socket connection (responses/events)"""
        try:
            # Keep connection alive for real-time messages
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()

    async def _process_command(self, command: str) -> str:
        """Process a command and return response"""
        parts = command.split()
        if not parts:
            return "resp error: empty command"

        cmd = parts[0]

        try:
            if cmd == "add_plugin":
                # add_plugin <uri> <instance> <x> <y>
                if len(parts) >= 4:
                    uri, instance, x, y = (
                        parts[1],
                        parts[2],
                        float(parts[3]),
                        float(parts[4]),
                    )
                    self.plugins[instance] = {
                        "uri": uri,
                        "x": x,
                        "y": y,
                        "ports": {},
                        "bypass": False,
                    }
                    return "resp 0"
                return "resp -1"

            elif cmd == "remove_plugin":
                # remove_plugin <instance>
                if len(parts) >= 2:
                    instance = parts[1]
                    if instance in self.plugins:
                        del self.plugins[instance]
                        return "resp 0"
                return "resp -1"

            elif cmd == "param_set":
                # param_set <instance> <symbol> <value>
                if len(parts) >= 4:
                    instance, symbol, value = parts[1], parts[2], float(parts[3])
                    if instance in self.plugins:
                        self.plugins[instance]["ports"][symbol] = value
                        return "resp 0"
                return "resp -1"

            elif cmd == "connect":
                # connect <from_port> <to_port>
                if len(parts) >= 3:
                    from_port, to_port = parts[1], parts[2]
                    self.connections.append((from_port, to_port))
                    return "resp 0"
                return "resp -1"

            elif cmd == "disconnect":
                # disconnect <from_port> <to_port>
                if len(parts) >= 3:
                    from_port, to_port = parts[1], parts[2]
                    if (from_port, to_port) in self.connections:
                        self.connections.remove((from_port, to_port))
                    return "resp 0"
                return "resp -1"

            elif cmd == "bpm":
                # bpm <value>
                if len(parts) >= 2:
                    self.transport["bpm"] = float(parts[1])
                    return "resp 0"
                return "resp -1"

            elif cmd == "transport":
                # transport (start)
                self.transport["rolling"] = True
                return "resp 0"

            elif cmd == "transport_stop":
                # transport_stop
                self.transport["rolling"] = False
                return "resp 0"

            else:
                return f"resp error: unknown command {cmd}"

        except Exception as e:
            return f"resp error: {e}"


@pytest.fixture
async def mock_modhost():
    """Fixture providing a mock mod-host instance"""
    mock = MockModHost()
    await mock.start()
    yield mock
    await mock.stop()


@pytest.fixture
async def audio_service(mock_modhost):
    """Fixture providing an audio engine service connected to mock mod-host"""
    service = AudioEngineService()
    success = await service.start()
    assert success, "Failed to start audio engine service"
    yield service
    await service.stop()


class TestAudioEngineService:
    """Test suite for Audio Engine Service"""

    async def test_connection(self, audio_service):
        """Test basic connection to mod-host"""
        assert audio_service.is_connected

    async def test_add_plugin(self, audio_service):
        """Test adding a plugin"""
        command = AddPluginCommand(
            instance_id="test_plugin_1",
            plugin_uri="http://example.com/plugin",
            x=100.0,
            y=200.0,
        )

        plugin = await audio_service.add_plugin(command)

        assert plugin.instance_id == "test_plugin_1"
        assert plugin.plugin_uri == "http://example.com/plugin"
        assert plugin.x == 100.0
        assert plugin.y == 200.0

        # Check state was updated
        state = await audio_service.get_state()
        assert "test_plugin_1" in state.plugins

    async def test_remove_plugin(self, audio_service):
        """Test removing a plugin"""
        # First add a plugin
        add_cmd = AddPluginCommand(
            instance_id="test_plugin_2", plugin_uri="http://example.com/plugin2"
        )
        await audio_service.add_plugin(add_cmd)

        # Then remove it
        remove_cmd = RemovePluginCommand(instance_id="test_plugin_2")
        success = await audio_service.remove_plugin(remove_cmd)

        assert success

        # Check state was updated
        state = await audio_service.get_state()
        assert "test_plugin_2" not in state.plugins

    async def test_set_parameter(self, audio_service):
        """Test setting plugin parameter"""
        # First add a plugin
        add_cmd = AddPluginCommand(
            instance_id="test_plugin_3", plugin_uri="http://example.com/plugin3"
        )
        await audio_service.add_plugin(add_cmd)

        # Set parameter
        param_cmd = SetParameterCommand(
            instance_id="test_plugin_3", port_symbol="gain", value=0.75
        )
        success = await audio_service.set_parameter(param_cmd)

        assert success

        # Check state was updated
        state = await audio_service.get_state()
        plugin = state.plugins["test_plugin_3"]
        assert plugin.ports["gain"] == 0.75

    async def test_connect_ports(self, audio_service):
        """Test connecting audio ports"""
        command = ConnectPortsCommand(
            from_port="system:capture_1", to_port="test_plugin:input"
        )

        connection = await audio_service.connect_ports(command)

        assert connection.from_port == "system:capture_1"
        assert connection.to_port == "test_plugin:input"

        # Check state was updated
        state = await audio_service.get_state()
        assert len(state.connections) > 0

    async def test_transport_control(self, audio_service):
        """Test transport control"""
        # Set BPM
        bpm_cmd = SetTransportCommand(bpm=140.0)
        transport = await audio_service.set_transport(bpm_cmd)
        assert transport.bpm == 140.0

        # Start transport
        play_cmd = SetTransportCommand(rolling=True)
        transport = await audio_service.set_transport(play_cmd)
        assert transport.rolling is True

        # Stop transport
        stop_cmd = SetTransportCommand(rolling=False)
        transport = await audio_service.set_transport(stop_cmd)
        assert transport.rolling is False


class TestAudioEngineHTTPAPI:
    """Test HTTP API endpoints"""

    @pytest.fixture
    async def client(self, mock_modhost):
        """HTTP client fixture"""
        # Import here to avoid issues with service startup
        from src.mod_ui.services.audio_engine.main import app

        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "connected" in data

    async def test_add_plugin_endpoint(self, client):
        """Test add plugin HTTP endpoint"""
        payload = {
            "instance_id": "http_test_plugin",
            "plugin_uri": "http://example.com/http_plugin",
            "x": 50.0,
            "y": 100.0,
        }

        response = await client.post("/plugins", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == "http_test_plugin"

    async def test_transport_endpoint(self, client):
        """Test transport control endpoint"""
        # Get current transport state
        response = await client.get("/transport")
        assert response.status_code == 200

        # Set BPM
        response = await client.post("/transport/bpm?bpm=128")
        assert response.status_code == 200
        data = response.json()
        assert data["bpm"] == 128.0


if __name__ == "__main__":
    """Run tests manually"""
    import os
    import sys

    # Add project root to path
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    )

    async def run_basic_test():
        """Run a basic integration test"""
        print("Starting audio engine integration test...")

        # Start mock mod-host
        mock = MockModHost()
        await mock.start()

        try:
            # Start audio service
            service = AudioEngineService()
            success = await service.start()

            if not success:
                print("❌ Failed to connect to mod-host")
                return

            print("✅ Connected to mod-host")

            # Test plugin operations
            print("Testing plugin operations...")

            # Add plugin
            add_cmd = AddPluginCommand(
                instance_id="test_plugin",
                plugin_uri="http://example.com/test",
                x=100.0,
                y=200.0,
            )
            plugin = await service.add_plugin(add_cmd)
            print(f"✅ Added plugin: {plugin.instance_id}")

            # Set parameter
            param_cmd = SetParameterCommand(
                instance_id="test_plugin", port_symbol="volume", value=0.8
            )
            await service.set_parameter(param_cmd)
            print("✅ Set parameter")

            # Test transport
            transport_cmd = SetTransportCommand(bpm=130.0, rolling=True)
            transport = await service.set_transport(transport_cmd)
            print(f"✅ Set transport: BPM={transport.bpm}, Playing={transport.rolling}")

            # Get state
            state = await service.get_state()
            print(
                f"✅ Current state: {len(state.plugins)} plugins, {len(state.connections)} connections"
            )

            print("🎉 All tests passed!")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            await service.stop()
            await mock.stop()

    # Run the test
    asyncio.run(run_basic_test())
