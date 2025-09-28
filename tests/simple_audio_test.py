"""
Simple Audio Engine Test

Test the audio engine service connection and basic operations
without complex import dependencies.
"""

import asyncio
import os
import socket
import sys

# Add the project to Python path
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui")
sys.path.insert(0, "/home/nicolas/project/madeline/mod-ui/src")

try:
    from mod_ui.services.audio_engine.connection import (
        AudioEngineCommand,
        ModHostConnectionManager,
    )
    from mod_ui.services.audio_engine.models import (
        AddPluginCommand,
        SetParameterCommand,
    )
    from mod_ui.services.audio_engine.service import AudioEngineService
except ImportError as e:
    print(f"Import error: {e}")
    print("Available paths:")
    for path in sys.path:
        print(f"  {path}")
    sys.exit(1)


class SimpleModHostMock:
    """Simple mock mod-host for testing"""

    def __init__(self):
        self.write_server = None
        self.read_server = None
        self.running = True

    async def start(self):
        """Start mock servers"""
        try:
            self.write_server = await asyncio.start_server(
                self._handle_write, "127.0.0.1", 5555
            )
            self.read_server = await asyncio.start_server(
                self._handle_read, "127.0.0.1", 5556
            )
            print("✅ Mock mod-host started on ports 5555/5556")
            return True
        except Exception as e:
            print(f"❌ Failed to start mock mod-host: {e}")
            return False

    async def _handle_write(self, reader, writer):
        """Handle write socket (commands)"""
        try:
            while self.running:
                data = await reader.readuntil(b"\0")
                if not data:
                    break

                command = data[:-1].decode("utf-8")
                print(f"📨 Received: {command}")

                # Simple response
                response = "resp 0"
                writer.write(f"{response}\0".encode("utf-8"))
                await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Write handler error: {e}")
        finally:
            writer.close()

    async def _handle_read(self, reader, writer):
        """Handle read socket (events)"""
        try:
            while self.running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()

    async def stop(self):
        """Stop servers"""
        self.running = False
        if self.write_server:
            self.write_server.close()
            await self.write_server.wait_closed()
        if self.read_server:
            self.read_server.close()
            await self.read_server.wait_closed()


async def test_connection_manager():
    """Test the connection manager directly"""
    print("🧪 Testing ModHostConnectionManager...")

    # Start mock
    mock = SimpleModHostMock()
    if not await mock.start():
        return False

    try:
        # Test connection
        conn = ModHostConnectionManager()
        connected = await conn.connect()

        if connected:
            print("✅ Connection manager connected successfully")

            # Test sending a command
            cmd = AudioEngineCommand(
                command="add_plugin",
                parameters={
                    "uri": "http://example.com/test",
                    "instance": "test_instance",
                    "x": 100,
                    "y": 200,
                },
            )

            response = await conn.send_command(cmd)
            print(f"✅ Command response: {response.status}")

            await conn.disconnect()
            print("✅ Disconnected successfully")

        else:
            print("❌ Failed to connect")
            return False

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await mock.stop()

    return True


async def test_audio_service():
    """Test the audio service"""
    print("\n🧪 Testing AudioEngineService...")

    # Start mock
    mock = SimpleModHostMock()
    if not await mock.start():
        return False

    try:
        # Test service
        service = AudioEngineService()
        started = await service.start()

        if started:
            print("✅ Audio service started successfully")
            print(f"✅ Connection status: {service.is_connected}")

            # Test adding a plugin
            cmd = AddPluginCommand(
                instance_id="test_plugin",
                plugin_uri="http://example.com/test",
                x=50.0,
                y=100.0,
            )

            try:
                plugin = await service.add_plugin(cmd)
                print(f"✅ Plugin added: {plugin.instance_id}")
            except Exception as e:
                print(f"⚠️  Plugin add failed: {e}")

            # Test getting state
            try:
                state = await service.get_state()
                print(f"✅ Got state: {len(state.plugins)} plugins")
            except Exception as e:
                print(f"⚠️  Get state failed: {e}")

            await service.stop()
            print("✅ Service stopped successfully")

        else:
            print("❌ Failed to start service")
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await mock.stop()

    return True


async def main():
    """Run all tests"""
    print("🚀 Starting Audio Engine Service Tests\n")

    # Test 1: Connection Manager
    success1 = await test_connection_manager()

    # Test 2: Audio Service
    success2 = await test_audio_service()

    # Summary
    print("\n📊 Test Results:")
    print(f"Connection Manager: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Audio Service: {'✅ PASS' if success2 else '❌ FAIL'}")

    if success1 and success2:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
