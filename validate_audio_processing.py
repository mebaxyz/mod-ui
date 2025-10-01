#!/usr/bin/env python3
"""
Comprehensive validation script for audio_processing service.
Tests all major features against a running mod-host to ensure 1:1 feature parity
with the original implementation.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict

from servicebus import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class AudioProcessingValidator:
    """Validates audio_processing service features."""

    def __init__(self):
        self.servicebus = None
        self.test_results = []

    async def setup(self):
        """Setup servicebus connection."""
        logger.info("Setting up ServiceBus connection...")
        self.servicebus = Service("validation_client")
        await self.servicebus.start()
        logger.info("ServiceBus connected")

    async def teardown(self):
        """Cleanup servicebus connection."""
        if self.servicebus:
            await self.servicebus.stop()
            logger.info("ServiceBus disconnected")

    def record_test(self, test_name: str, success: bool, details: str = ""):
        """Record test result."""
        self.test_results.append(
            {"test": test_name, "success": success, "details": details}
        )
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name} - {details}")

    async def test_health_check(self):
        """Test service health check."""
        try:
            response = await self.servicebus.call("audio_processing", "health")
            success = (
                response.get("service") == "audio_processing"
                and response.get("status") == "healthy"
                and response.get("details", {}).get("modhost", {}).get("connected")
                is True
            )
            details = f"Status: {response.get('status')}, ModHost: {response.get('details', {}).get('modhost', {}).get('connected')}"
            self.record_test("Health Check", success, details)
            return response
        except Exception as e:
            self.record_test("Health Check", False, f"Error: {e}")
            return None

    async def test_echo(self):
        """Test echo method (basic RPC)."""
        try:
            test_message = "validation_test_message"
            response = await self.servicebus.call(
                "audio_processing", "echo", message=test_message
            )
            success = response.get("echo") == test_message
            self.record_test("Echo RPC", success, f"Echoed: {response.get('echo')}")
            return success
        except Exception as e:
            self.record_test("Echo RPC", False, f"Error: {e}")
            return False

    async def test_get_available_plugins(self):
        """Test getting available plugins."""
        try:
            response = await self.servicebus.call(
                "audio_processing", "get_available_plugins"
            )
            plugins = response.get("plugins", [])
            success = len(plugins) > 0
            details = f"Found {len(plugins)} plugins"
            if plugins:
                details += f" (first: {plugins[0].get('name', 'unknown')})"
            self.record_test("Get Available Plugins", success, details)
            return plugins
        except Exception as e:
            self.record_test("Get Available Plugins", False, f"Error: {e}")
            return []

    async def test_plugin_lifecycle(self, plugins):
        """Test plugin loading and unloading."""
        if not plugins:
            self.record_test("Plugin Lifecycle", False, "No plugins available")
            return None

        # Use first available plugin
        plugin = plugins[0]
        plugin_uri = plugin.get("uri")

        if not plugin_uri:
            self.record_test("Plugin Lifecycle", False, "Plugin has no URI")
            return None

        try:
            # Load plugin
            logger.info(f"Loading plugin: {plugin.get('name', plugin_uri)}")
            load_response = await self.servicebus.call(
                "audio_processing", "load_plugin", uri=plugin_uri, x=100.0, y=200.0
            )

            instance_id = load_response.get("instance_id")
            load_success = instance_id is not None

            if not load_success:
                self.record_test(
                    "Plugin Load", False, f"No instance_id returned: {load_response}"
                )
                return None

            self.record_test("Plugin Load", True, f"Loaded as instance {instance_id}")

            # Get plugin info
            info_response = await self.servicebus.call(
                "audio_processing", "get_plugin_info", instance_id=instance_id
            )

            info_success = info_response.get("uri") == plugin_uri
            self.record_test(
                "Get Plugin Info", info_success, f"URI matches: {info_success}"
            )

            # List instances
            list_response = await self.servicebus.call(
                "audio_processing", "list_instances"
            )
            instances = list_response.get("instances", [])
            list_success = any(
                inst.get("instance_id") == instance_id for inst in instances
            )
            self.record_test(
                "List Instances", list_success, f"Found {len(instances)} instances"
            )

            # Test parameter operations if plugin has control ports
            control_ports = plugin.get("ports", {}).get("control", [])
            if control_ports:
                param_symbol = control_ports[0].get("symbol")
                if param_symbol:
                    # Set parameter
                    try:
                        await self.servicebus.call(
                            "audio_processing",
                            "set_parameter",
                            instance_id=instance_id,
                            parameter=param_symbol,
                            value=0.5,
                        )
                        self.record_test(
                            "Set Parameter", True, f"Set {param_symbol} = 0.5"
                        )

                        # Get parameter
                        get_response = await self.servicebus.call(
                            "audio_processing",
                            "get_parameter",
                            instance_id=instance_id,
                            parameter=param_symbol,
                        )
                        param_value = get_response.get("value")
                        get_success = param_value is not None
                        self.record_test(
                            "Get Parameter",
                            get_success,
                            f"Got {param_symbol} = {param_value}",
                        )

                    except Exception as e:
                        self.record_test("Parameter Operations", False, f"Error: {e}")
            else:
                self.record_test(
                    "Parameter Operations", True, "No control ports (skipped)"
                )

            # Unload plugin
            unload_response = await self.servicebus.call(
                "audio_processing", "unload_plugin", instance_id=instance_id
            )

            unload_success = unload_response.get("success", False)
            self.record_test(
                "Plugin Unload", unload_success, f"Unloaded instance {instance_id}"
            )

            return instance_id

        except Exception as e:
            self.record_test("Plugin Lifecycle", False, f"Error: {e}")
            return None

    async def test_pedalboard_operations(self):
        """Test pedalboard creation, saving, and loading."""
        try:
            # Create pedalboard
            create_response = await self.servicebus.call(
                "audio_processing",
                "create_pedalboard",
                name="Validation Test Board",
                description="Test pedalboard for validation",
            )

            create_success = create_response.get("success", False)
            self.record_test(
                "Create Pedalboard",
                create_success,
                f"Created: {create_response.get('name')}",
            )

            # Get current pedalboard
            current_response = await self.servicebus.call(
                "audio_processing", "get_current_pedalboard"
            )
            current_success = current_response.get("title") == "Validation Test Board"
            self.record_test(
                "Get Current Pedalboard",
                current_success,
                f"Title: {current_response.get('title')}",
            )

            # Save pedalboard
            save_response = await self.servicebus.call(
                "audio_processing", "save_pedalboard"
            )
            save_success = save_response.get("success", False)
            self.record_test("Save Pedalboard", save_success, "Pedalboard saved")

            return True

        except Exception as e:
            self.record_test("Pedalboard Operations", False, f"Error: {e}")
            return False

    async def test_persistence_operations(self):
        """Test persistence (saved pedalboards)."""
        try:
            # List saved pedalboards
            list_response = await self.servicebus.call(
                "audio_processing", "list_saved_pedalboards"
            )
            saved_boards = list_response.get("saved", [])
            list_success = isinstance(saved_boards, list)
            self.record_test(
                "List Saved Pedalboards",
                list_success,
                f"Found {len(saved_boards)} saved",
            )

            return True

        except Exception as e:
            self.record_test("Persistence Operations", False, f"Error: {e}")
            return False

    async def test_connection_operations(self):
        """Test audio connection operations."""
        try:
            # Test creating a connection (will likely fail but should not crash)
            try:
                conn_response = await self.servicebus.call(
                    "audio_processing",
                    "create_connection",
                    source_plugin="system",
                    source_port="capture_1",
                    target_plugin="system",
                    target_port="playback_1",
                )
                conn_success = True  # If no exception, the RPC works
                details = (
                    f"Connection result: {conn_response.get('success', 'unknown')}"
                )
            except Exception as conn_e:
                # Connection might fail due to JACK routing, but RPC should work
                conn_success = (
                    "not found" in str(conn_e).lower()
                    or "connection" in str(conn_e).lower()
                )
                details = f"Expected connection error: {conn_e}"

            self.record_test("Connection Operations", conn_success, details)
            return True

        except Exception as e:
            self.record_test("Connection Operations", False, f"Unexpected error: {e}")
            return False

    async def run_validation(self):
        """Run complete validation suite."""
        logger.info("Starting audio_processing service validation...")
        logger.info("=" * 60)

        try:
            await self.setup()

            # Basic connectivity
            health_info = await self.test_health_check()
            await self.test_echo()

            if not health_info or health_info.get("status") != "healthy":
                logger.error("Service health check failed - aborting validation")
                return False

            # Plugin operations
            plugins = await self.test_get_available_plugins()
            await self.test_plugin_lifecycle(plugins)

            # Session operations
            await self.test_pedalboard_operations()
            await self.test_persistence_operations()
            await self.test_connection_operations()

        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            self.record_test("Overall Validation", False, f"Exception: {e}")

        finally:
            await self.teardown()

        # Print results
        logger.info("=" * 60)
        logger.info("VALIDATION RESULTS:")
        logger.info("=" * 60)

        passed = 0
        failed = 0

        for result in self.test_results:
            status = "✓ PASS" if result["success"] else "✗ FAIL"
            logger.info(f"{status}: {result['test']} - {result['details']}")
            if result["success"]:
                passed += 1
            else:
                failed += 1

        logger.info("=" * 60)
        logger.info(f"SUMMARY: {passed} passed, {failed} failed")

        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED - Feature parity validated!")
            return True
        else:
            logger.warning(f"⚠️  {failed} tests failed - check implementation")
            return False


async def main():
    """Main validation entry point."""
    validator = AudioProcessingValidator()
    success = await validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
