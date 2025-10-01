#!/usr/bin/env python3
"""
Test script for Phase 1 Critical mod-host commands
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from libraries.servicebus.servicebus import Service


async def test_phase1_commands():
    """Test the Phase 1 Critical mod-host commands"""

    print("🧪 TESTING PHASE 1 CRITICAL MOD-HOST COMMANDS")
    print("=" * 60)

    # Connect as client to existing audio processing service
    service_bus = Service("test_client")  # Client with unique name
    await service_bus.start()

    try:
        # Test 1: Health check
        print("\n1. Health Check")
        health = await service_bus.call("audio_processing", "health")
        print(f"   ✅ Service health: {health}")

        # Test 2: Get CPU Load
        print("\n2. Get CPU Load")
        try:
            cpu_result = await service_bus.call("audio_processing", "get_cpu_load")
            print(f"   ✅ CPU Load: {cpu_result}")
        except Exception as e:
            print(f"   ❌ CPU Load failed: {e}")

        # Test 3: Get Max CPU Load
        print("\n3. Get Max CPU Load")
        try:
            max_cpu_result = await service_bus.call(
                "audio_processing", "get_max_cpu_load"
            )
            print(f"   ✅ Max CPU Load: {max_cpu_result}")
        except Exception as e:
            print(f"   ❌ Max CPU Load failed: {e}")

        # Test 4: Preload Plugin
        print("\n4. Preload Plugin")
        try:
            preload_result = await service_bus.call(
                "audio_processing",
                "preload_plugin",
                lv2_uri="http://guitarix.sourceforge.net/plugins/gx_amp#GUITARIX",
            )
            print(f"   ✅ Preload Plugin: {preload_result}")
        except Exception as e:
            print(f"   ❌ Preload Plugin failed: {e}")

        # Test 5: Disconnect All Ports
        print("\n5. Disconnect All Ports")
        try:
            disconnect_result = await service_bus.call(
                "audio_processing", "disconnect_all_ports"
            )
            print(f"   ✅ Disconnect All: {disconnect_result}")
        except Exception as e:
            print(f"   ❌ Disconnect All failed: {e}")

        # Test 6: Load and Activate Plugin
        print("\n6. Load Plugin for Activation Test")
        try:
            # First load a plugin
            load_result = await service_bus.call(
                "audio_processing",
                "load_plugin",
                uri="http://guitarix.sourceforge.net/plugins/gx_amp#GUITARIX",
                x=100,
                y=100,
            )
            print(f"   ✅ Load Plugin: {load_result}")

            if load_result.get("success") and "instance_id" in load_result:
                instance_id = load_result["instance_id"]

                # Test Activate Plugin
                print("\n7. Activate Plugin")
                activate_result = await service_bus.call(
                    "audio_processing", "activate_plugin", instance_number=instance_id
                )
                print(f"   ✅ Activate Plugin: {activate_result}")

                # Test Bypass Plugin
                print("\n8. Bypass Plugin")
                bypass_result = await service_bus.call(
                    "audio_processing",
                    "bypass_plugin",
                    instance_number=instance_id,
                    bypass=True,
                )
                print(f"   ✅ Bypass Plugin: {bypass_result}")

                # Test Enable Plugin (un-bypass)
                print("\n9. Enable Plugin (un-bypass)")
                enable_result = await service_bus.call(
                    "audio_processing",
                    "bypass_plugin",
                    instance_number=instance_id,
                    bypass=False,
                )
                print(f"   ✅ Enable Plugin: {enable_result}")

        except Exception as e:
            print(f"   ❌ Plugin activation tests failed: {e}")

        print("\n" + "=" * 60)
        print("🎉 PHASE 1 CRITICAL COMMANDS TEST COMPLETE")

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        raise
    finally:
        await service_bus.stop()


if __name__ == "__main__":
    asyncio.run(test_phase1_commands())
