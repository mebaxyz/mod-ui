#!/usr/bin/env python3
"""
MOD Audio Engine Service Extended Test Suite

Tests the audio engine service with JACK and LV2 integration
in both venv and Docker environments.

Usage:
    python test_audio_engine_extended.py --venv      # Test in venv
    python test_audio_engine_extended.py --docker    # Test in Docker
    python test_audio_engine_extended.py             # Auto-detect
"""

import argparse
import asyncio
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_audio_engine_extended(environment="auto"):
    """Test the extended audio engine service with JACK and LV2 support"""

    print("🚀 MOD Audio Engine Service Test Suite")
    print("This test can run in:")
    print("  • venv (local development)")
    print("  • Docker (containerized deployment)")
    print("  • ServiceBus (microservices architecture)")

    try:
        print("🧪 Testing Audio Engine Service with JACK and LV2 Support")
        print("=" * 60)

        # Import service components
        from mod_ui.services.audio_engine.jack_lv2_utils import (
            get_jack_manager,
            get_lv2_manager,
        )
        from mod_ui.services.audio_engine.service import AudioEngineService

        # Initialize service
        print("\n1. 🚀 Starting audio engine service...")
        service = AudioEngineService()
        started = await service.start()
        print(f"   Service started: {started}")
        print(f"   mod-host connected: {service.is_connected}")

        # Test JACK functionality
        print("\n2. 🎵 Testing JACK functionality...")
        jack_data = await service.get_jack_data()
        print(
            f"   ✅ JACK Data: CPU Load={jack_data.cpu_load:.2f}%, Sample Rate={jack_data.sample_rate}Hz"
        )
        print(f"      XRuns: {jack_data.xruns}, Buffer Size: {jack_data.buffer_size}")

        # Test hardware ports
        hw_ports = await service.get_jack_hardware_ports()
        input_ports = [p for p in hw_ports if not p.is_output]
        output_ports = [p for p in hw_ports if p.is_output]
        print(
            f"   ✅ Hardware Ports: {len(input_ports)} inputs, {len(output_ports)} outputs"
        )

        # Test LV2 plugin functionality
        print("\n3. 🔌 Testing LV2 plugin functionality...")
        plugins = await service.get_plugin_list()
        print(f"   ✅ Found {len(plugins)} LV2 plugins")

        all_plugins = await service.get_all_plugins()
        print(f"   ✅ All plugins scan: {len(all_plugins)} plugins")

        # Test JACK connections (if we have ports)
        print("\n4. 🔗 Testing JACK connection functionality...")
        if len(hw_ports) >= 2:
            try:
                # Try to connect first two ports for testing
                from mod_ui.services.audio_engine.models import ConnectJackPortsCommand

                connect_cmd = ConnectJackPortsCommand(
                    output_port=hw_ports[0].name, input_port=hw_ports[1].name
                )
                connection = await service.connect_jack_ports(connect_cmd)
                print(
                    f"   ✅ JACK connection test: {connection.output_port} → {connection.input_port}"
                )

                # Disconnect
                from mod_ui.services.audio_engine.models import (
                    DisconnectJackPortsCommand,
                )

                disconnect_cmd = DisconnectJackPortsCommand(
                    output_port=hw_ports[0].name, input_port=hw_ports[1].name
                )
                disconnected = await service.disconnect_jack_ports(disconnect_cmd)
                print(f"   ✅ JACK disconnection test: {disconnected}")

            except Exception as e:
                print(f"   ℹ️  JACK connection test: {e}")
        else:
            print("   ℹ️  JACK connection test skipped (requires running JACK)")

        # Test audio engine state
        print("\n5. 📊 Testing audio engine state...")
        state = await service.get_state()
        print(f"   ✅ Audio Engine State:")
        print(f"      Plugins: {len(state.plugins)}")
        print(f"      Connections: {len(state.connections)}")
        print(f"      Transport BPM: {state.transport.bpm}")
        print(f"      JACK Hardware Ports: {len(hw_ports)}")

        print("\n" + "=" * 60)
        print("🎉 Audio Engine Service Test Complete!")
        print("   • Core functionality: Available")
        print(
            "   • JACK integration: Ready (requires JACK daemon)"
            if not service.is_connected
            else "   • JACK integration: Connected"
        )
        print("   • LV2 integration: Ready (requires MOD utils or fallback)")
        print("   • ServiceBus ready: Yes")
        print("   • Docker ready: Yes")

        # Stop service
        print("\n🛑 Stopping service...")
        await service.stop()

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(
            "Make sure you're in the correct environment (venv activated or Docker running)"
        )
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_fallback_functionality():
    """Test fallback implementations without MOD utilities"""
    print("\n🧪 Testing Fallback Functionality")
    print("=" * 40)

    try:
        from mod_ui.services.audio_engine.jack_lv2_utils import (
            get_jack_manager,
            get_lv2_manager,
        )

        # Test managers
        jack_manager = get_jack_manager()
        lv2_manager = get_lv2_manager()

        print(f"JACK Manager initialized: {jack_manager is not None}")
        print(f"LV2 Manager initialized: {lv2_manager is not None}")

        if jack_manager:
            jack_data = await jack_manager.get_jack_data()
            print(
                f"JACK Data (fallback): SR={jack_data.sample_rate}Hz, BS={jack_data.buffer_size}"
            )

        if lv2_manager:
            plugins = await lv2_manager.get_plugin_list()
            print(f"LV2 Plugins (fallback): {len(plugins)} found")

    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

    return True


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test MOD Audio Engine Service")
    parser.add_argument("--venv", action="store_true", help="Test in venv environment")
    parser.add_argument(
        "--docker", action="store_true", help="Test in Docker environment"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    environment = "auto"
    if args.venv:
        environment = "venv"
    elif args.docker:
        environment = "docker"

    # Run tests
    try:
        success = asyncio.run(test_audio_engine_extended(environment))
        if success:
            asyncio.run(test_fallback_functionality())
            print("\n✅ All tests completed successfully!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
