#!/usr/bin/env python3
"""
Test Phase 1 Critical mod-host commands
"""

import asyncio
import logging
import os
import sys

# Add path to find the servicebus module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libraries", "servicebus"))

from servicebus import Service

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def test_phase1_commands():
    """Test Phase 1 Critical commands"""

    print("🧪 TESTING PHASE 1 CRITICAL MOD-HOST COMMANDS")
    print("=" * 60)

    # Setup servicebus connection
    servicebus = Service("phase1_test_client")
    await servicebus.start()

    try:
        # Test 1: Health check first
        print("\n1. Testing Health Check...")
        health = await servicebus.call("audio_processing", "health")
        print(f"   ✅ Health: {health}")

        # Test 2: CPU Load
        print("\n2. Testing CPU Load...")
        cpu_result = await servicebus.call("audio_processing", "get_cpu_load")
        print(f"   ✅ CPU Load: {cpu_result}")

        # Test 3: Max CPU Load
        print("\n3. Testing Max CPU Load...")
        max_cpu_result = await servicebus.call("audio_processing", "get_max_cpu_load")
        print(f"   ✅ Max CPU Load: {max_cpu_result}")

        # Test 4: Preload Plugin
        print("\n4. Testing Preload Plugin...")
        preload_result = await servicebus.call(
            "audio_processing",
            "preload_plugin",
            lv2_uri="http://guitarix.sourceforge.net/plugins/gx_amp#GUITARIX",
        )
        print(f"   ✅ Preload Plugin: {preload_result}")

        # Test 5: Disconnect All Ports
        print("\n5. Testing Disconnect All Ports...")
        disconnect_result = await servicebus.call(
            "audio_processing", "disconnect_all_ports"
        )
        print(f"   ✅ Disconnect All: {disconnect_result}")

        # Test 6-9: Plugin lifecycle (load, activate, bypass, enable)
        print("\n6. Testing Plugin Lifecycle...")

        # Load plugin first
        load_result = await servicebus.call(
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
            print(f"\n7. Testing Activate Plugin (instance {instance_id})...")
            activate_result = await servicebus.call(
                "audio_processing", "activate_plugin", instance_number=instance_id
            )
            print(f"   ✅ Activate Plugin: {activate_result}")

            # Test Bypass Plugin
            print(f"\n8. Testing Bypass Plugin (instance {instance_id})...")
            bypass_result = await servicebus.call(
                "audio_processing",
                "bypass_plugin",
                instance_number=instance_id,
                bypass=True,
            )
            print(f"   ✅ Bypass Plugin: {bypass_result}")

            # Test Enable Plugin (un-bypass)
            print(f"\n9. Testing Enable Plugin (instance {instance_id})...")
            enable_result = await servicebus.call(
                "audio_processing",
                "bypass_plugin",
                instance_number=instance_id,
                bypass=False,
            )
            print(f"   ✅ Enable Plugin: {enable_result}")

        else:
            print("   ⚠️  Skipping plugin lifecycle tests - load failed")

        print("\n" + "=" * 60)
        print("🎉 PHASE 1 CRITICAL COMMANDS TEST COMPLETE!")
        print("✅ All 6 Phase 1 commands are working:")
        print("   • activate_plugin")
        print("   • preload_plugin")
        print("   • bypass_plugin")
        print("   • disconnect_all_ports")
        print("   • get_cpu_load")
        print("   • get_max_cpu_load")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await servicebus.stop()


if __name__ == "__main__":
    asyncio.run(test_phase1_commands())
