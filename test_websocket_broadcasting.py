#!/usr/bin/env python3
"""
Test script for WebSocket broadcasting functionality

Tests all implemented WebSocket message types:
- Plugin operations (add, remove, parameter changes)
- Preset management (load, save)
- Snapshot management (load, save)
- System stats (automatic broadcasting)
- Connection management (connect, disconnect)
- Hardware control (infrastructure ready)
"""

import json
import time

import requests

BASE_URL = "http://localhost:8081"


def test_plugin_operations():
    """Test plugin WebSocket broadcasting"""
    print("\n=== Testing Plugin Operations ===")

    # Test plugin add
    print("1. Plugin Add...")
    response = requests.get(
        f"{BASE_URL}/api/effect/add/test_plugin?uri=http://example.com/plugin&x=100&y=200"
    )
    print(f"   Status: {response.status_code}, Response: {response.text[:100]}...")

    # Test parameter change
    print("2. Parameter Change...")
    response = requests.get(
        f"{BASE_URL}/api/effect/parameter/set/test_plugin?symbol=gain&value=0.8"
    )
    print(f"   Status: {response.status_code}, Response: {response.text}")

    # Test plugin remove
    print("3. Plugin Remove...")
    response = requests.get(f"{BASE_URL}/api/effect/remove/test_plugin")
    print(f"   Status: {response.status_code}, Response: {response.text}")


def test_preset_management():
    """Test preset WebSocket broadcasting"""
    print("\n=== Testing Preset Management ===")

    # Test preset load
    print("1. Preset Load...")
    response = requests.get(
        f"{BASE_URL}/api/effect/preset/load/test_instance?preset_uri=test_preset.ttl"
    )
    print(f"   Status: {response.status_code}, Response: {response.text}")

    # Test preset save
    print("2. Preset Save...")
    response = requests.get(
        f"{BASE_URL}/api/effect/preset/save/test_instance?name=MyPreset"
    )
    print(f"   Status: {response.status_code}, Response: {response.text}")


def test_snapshot_management():
    """Test snapshot WebSocket broadcasting"""
    print("\n=== Testing Snapshot Management ===")

    # Test snapshot load
    print("1. Snapshot Load...")
    response = requests.get(f"{BASE_URL}/snapshot/load?id=1")
    print(f"   Status: {response.status_code}, Response: {response.text}")

    # Test snapshot save
    print("2. Snapshot Save As...")
    response = requests.get(f"{BASE_URL}/snapshot/saveas?title=TestSnapshot")
    print(f"   Status: {response.status_code}, Response: {response.text}")


def test_connection_management():
    """Test connection WebSocket broadcasting"""
    print("\n=== Testing Connection Management ===")

    # Test connection
    print("1. Connect Ports...")
    response = requests.get(f"{BASE_URL}/api/effect/connect/test_output/test_input")
    print(f"   Status: {response.status_code}, Response: {response.text}")

    # Test disconnection
    print("2. Disconnect Ports...")
    response = requests.get(f"{BASE_URL}/api/effect/disconnect/test_output/test_input")
    print(f"   Status: {response.status_code}, Response: {response.text}")


def check_system_stats():
    """Check system stats broadcasting (background)"""
    print("\n=== System Stats Broadcasting ===")
    print("System stats are automatically broadcast every 2 seconds in background")
    print(
        "Check webui-gateway logs for: POST /api/broadcast/broadcast from system-stats service"
    )


def main():
    """Run all WebSocket broadcasting tests"""
    print("🚀 Starting WebSocket Broadcasting Tests")
    print("=" * 50)

    # Wait a moment for services to be ready
    print("Waiting for services to be ready...")
    time.sleep(2)

    try:
        # Test all WebSocket broadcasting functionality
        test_plugin_operations()
        test_preset_management()
        test_snapshot_management()
        test_connection_management()
        check_system_stats()

        print("\n" + "=" * 50)
        print("✅ All WebSocket Broadcasting Tests Completed!")
        print("\nTo verify WebSocket messages were sent, check:")
        print("- docker logs mod-ui-webui-gateway --tail 20")
        print("- docker logs mod-ui-effects-service --tail 20")
        print("\nLook for: 'Successfully notified webui-gateway' messages")

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
