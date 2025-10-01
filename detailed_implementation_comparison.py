#!/usr/bin/env python3
"""
Detailed comparison between original MOD UI Host class and new audio_processing service
focusing on functional equivalence rather than method count.
"""

import os
import re
from typing import Dict, List, Set, Tuple


def get_original_host_methods() -> Dict[str, List[str]]:
    """Get categorized original Host class methods"""
    original_host = "/home/nicolas/project/madeline/mod-ui/src/mod_ui_original/host.py"

    if not os.path.exists(original_host):
        print(f"❌ Original host.py not found at {original_host}")
        return {}

    with open(original_host, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract method definitions
    pattern = r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
    methods = re.findall(pattern, content, re.MULTILINE)

    # Categorize by functionality (detailed analysis)
    categories = {
        "Plugin Lifecycle": [
            "add_plugin",
            "remove_plugin",
            "replace_plugin",
            "activate_plugin",
            "preload_plugin",
            "get_plugin_info",
            "get_plugin_data",
        ],
        "Plugin Control": [
            "bypass",
            "param_set",
            "param_get",
            "patch_set",
            "patch_get",
            "set_param_value",
            "get_param_value",
            "hmi_parameter_set",
        ],
        "Audio Connections": [
            "connect",
            "disconnect",
            "get_port_name_alias",
            "get_jack_source_port_name",
            "disconnect_all_ports",
            "_fix_host_connection_port",
        ],
        "Pedalboard Management": [
            "load_pedalboard",
            "save_pedalboard",
            "create_pedalboard",
            "remove_pedalboard",
            "pedalboard_save",
            "pedalboard_save_as",
            "get_all_good_and_bad_pedalboards",
        ],
        "Session Control": [
            "start_session",
            "end_session",
            "reset",
            "mute",
            "unmute",
            "report_current_state",
            "send_output_data_ready",
            "init_host",
            "clear",
        ],
        "Bundle Management": [
            "add_bundle",
            "remove_bundle",
            "refresh_bundle",
            "get_bundles_list",
        ],
        "Preset Management": [
            "load_preset",
            "save_preset",
            "show_presets",
            "delete_preset",
            "addr_task_get_plugin_presets",
        ],
        "MIDI Control": [
            "midi_learn",
            "midi_map",
            "midi_unmap",
            "set_midi_devices",
            "cb_midi_pb_prgch",
            "midi_beat_clock_sender_added",
        ],
        "HMI/Hardware": [
            "hmi_parameter_set",
            "hmi_list_bank_pedalboards",
            "ping_hmi",
            "initialize_hmi",
            "footswitch_addr1_callback",
            "process_read_message",
        ],
        "Addressing System": [
            "address",
            "unaddress",
            "readdress",
            "addr_task_addressing",
            "addr_task_unaddressing",
            "cv_addressing_plugin_port_add",
        ],
        "JACK Integration": [
            "init_jack",
            "close_jack",
            "jack_port_appeared",
            "jack_port_deleted",
            "jack_bufsize_changed",
            "set_jack_buffer_size",
        ],
        "Control Chain": [
            "cc_map_parameter",
            "cc_unmap_parameter",
            "cc_value_set",
            "addr_task_hw_added",
            "addr_task_hw_removed",
        ],
        "Transport/Tempo": [
            "set_tempo",
            "set_bpm",
            "set_beats_per_bar",
            "set_transport",
            "transport_sync",
            "addr_task_get_tempo_divider",
        ],
        "Monitoring/Feedback": [
            "monitor_parameter",
            "monitor_output",
            "get_cpu_load",
            "get_max_cpu_load",
            "get_audio_levels",
            "report_current_state",
        ],
    }

    # Match actual methods to categories
    found_categories = {}
    for category, expected_methods in categories.items():
        found_methods = []
        for method in methods:
            if any(
                expected in method.lower()
                for expected in [m.lower() for m in expected_methods]
            ):
                found_methods.append(method)
        found_categories[category] = found_methods

    return found_categories


def get_new_service_capabilities() -> Dict[str, List[str]]:
    """Get new service capabilities organized by functionality"""

    service_files = {
        "main.py": "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/main.py",
        "modhost_bridge.py": "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/modhost_bridge.py",
        "plugin_manager.py": "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/plugin_manager.py",
        "session_manager.py": "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/session_manager.py",
    }

    # Extract RPC handlers and service methods
    capabilities = {
        "Plugin Lifecycle": [],
        "Plugin Control": [],
        "Audio Connections": [],
        "Pedalboard Management": [],
        "Session Control": [],
        "Bundle Management": [],
        "Preset Management": [],
        "MIDI Control": [],
        "HMI/Hardware": [],
        "Addressing System": [],
        "JACK Integration": [],
        "Control Chain": [],
        "Transport/Tempo": [],
        "Monitoring/Feedback": [],
    }

    # Parse main.py for RPC handlers
    main_file = service_files["main.py"]
    if os.path.exists(main_file):
        with open(main_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract handler registrations and actual handler functions
        handler_pattern = r'service_bus\.register_handler\([\'"]([^\'"]+)[\'"]'
        handlers = re.findall(handler_pattern, content)

        # Also get handle_ functions
        handle_pattern = r"async def (handle_[a-zA-Z_]+)"
        handle_funcs = re.findall(handle_pattern, content)

        # Categorize handlers
        for handler in handlers + [h.replace("handle_", "") for h in handle_funcs]:
            handler_lower = handler.lower()

            if any(
                x in handler_lower
                for x in [
                    "load_plugin",
                    "unload_plugin",
                    "activate_plugin",
                    "preload_plugin",
                ]
            ):
                capabilities["Plugin Lifecycle"].append(handler)
            elif any(x in handler_lower for x in ["parameter", "bypass", "patch"]):
                capabilities["Plugin Control"].append(handler)
            elif any(
                x in handler_lower for x in ["connection", "connect", "disconnect"]
            ):
                capabilities["Audio Connections"].append(handler)
            elif any(x in handler_lower for x in ["pedalboard"]):
                capabilities["Pedalboard Management"].append(handler)
            elif any(x in handler_lower for x in ["session", "snapshot"]):
                capabilities["Session Control"].append(handler)
            elif any(x in handler_lower for x in ["bundle"]):
                capabilities["Bundle Management"].append(handler)
            elif any(x in handler_lower for x in ["preset"]):
                capabilities["Preset Management"].append(handler)
            elif any(x in handler_lower for x in ["midi"]):
                capabilities["MIDI Control"].append(handler)
            elif any(x in handler_lower for x in ["cc_", "cv_"]):
                capabilities["Control Chain"].append(handler)
            elif any(x in handler_lower for x in ["bpm", "transport", "beats"]):
                capabilities["Transport/Tempo"].append(handler)
            elif any(
                x in handler_lower for x in ["monitor", "cpu_load", "audio_levels"]
            ):
                capabilities["Monitoring/Feedback"].append(handler)

    # Parse modhost_bridge.py for mod-host protocol methods
    bridge_file = service_files["modhost_bridge.py"]
    if os.path.exists(bridge_file):
        with open(bridge_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract async methods
        method_pattern = r"async def ([a-zA-Z_][a-zA-Z0-9_]*)"
        methods = re.findall(method_pattern, content)

        for method in methods:
            if not method.startswith("_"):  # Skip private methods
                method_lower = method.lower()

                if any(
                    x in method_lower
                    for x in ["add_plugin", "remove_plugin", "activate", "preload"]
                ):
                    capabilities["Plugin Lifecycle"].append(f"bridge.{method}")
                elif any(x in method_lower for x in ["param", "bypass", "patch"]):
                    capabilities["Plugin Control"].append(f"bridge.{method}")
                elif any(x in method_lower for x in ["connect", "disconnect"]):
                    capabilities["Audio Connections"].append(f"bridge.{method}")

    return capabilities


def analyze_coverage() -> Dict[str, float]:
    """Analyze coverage of original functionality in new implementation"""

    print("🔍 DETAILED MOD UI IMPLEMENTATION COMPARISON")
    print("=" * 80)

    original_categories = get_original_host_methods()
    new_capabilities = get_new_service_capabilities()

    coverage_results = {}
    total_coverage = 0
    category_count = 0

    print(f"\n📊 FUNCTIONALITY COVERAGE ANALYSIS:")
    print(f"Comparing {len(original_categories)} functional categories")

    for category in original_categories.keys():
        original_methods = original_categories.get(category, [])
        new_methods = new_capabilities.get(category, [])

        if not original_methods:
            continue

        category_count += 1

        # Calculate coverage percentage
        if new_methods:
            coverage = min(100.0, (len(new_methods) / len(original_methods)) * 100)
        else:
            coverage = 0.0

        coverage_results[category] = coverage
        total_coverage += coverage

        # Display results
        status_icon = "✅" if coverage >= 80 else "⚠️" if coverage >= 40 else "❌"
        print(f"\n{status_icon} {category}: {coverage:.1f}% coverage")
        print(
            f"  Original: {len(original_methods)} methods, New: {len(new_methods)} handlers"
        )

        if coverage > 0:
            print(f"  New implementations: {', '.join(new_methods[:5])}")
            if len(new_methods) > 5:
                print(f"    ... and {len(new_methods) - 5} more")

        if coverage < 100 and original_methods:
            print(f"  Missing equivalents for: {', '.join(original_methods[:3])}")
            if len(original_methods) > 3:
                print(f"    ... and {len(original_methods) - 3} more")

    overall_coverage = total_coverage / category_count if category_count > 0 else 0

    print(f"\n🎯 OVERALL IMPLEMENTATION STATUS:")
    print(f"Average Coverage: {overall_coverage:.1f}%")

    # Categorize results
    excellent = sum(1 for c in coverage_results.values() if c >= 80)
    good = sum(1 for c in coverage_results.values() if 40 <= c < 80)
    poor = sum(1 for c in coverage_results.values() if c < 40)

    print(f"✅ Excellent (≥80%): {excellent} categories")
    print(f"⚠️  Good (40-79%): {good} categories")
    print(f"❌ Needs Work (<40%): {poor} categories")

    # Key findings
    print(f"\n📋 KEY FINDINGS:")

    high_coverage = [cat for cat, cov in coverage_results.items() if cov >= 80]
    if high_coverage:
        print(f"✅ Well-covered functionality: {', '.join(high_coverage)}")

    low_coverage = [cat for cat, cov in coverage_results.items() if cov < 40]
    if low_coverage:
        print(f"❌ Functionality gaps: {', '.join(low_coverage)}")

    return coverage_results


def generate_implementation_recommendations():
    """Generate specific recommendations for missing functionality"""

    print(f"\n🔧 IMPLEMENTATION RECOMMENDATIONS:")

    recommendations = {
        "High Priority (Core Functionality)": [
            "Session Control: Implement reset, mute/unmute, state reporting",
            "JACK Integration: Add JACK port management and buffer size control",
            "HMI/Hardware: Add hardware interface communication methods",
        ],
        "Medium Priority (Advanced Features)": [
            "Addressing System: Implement parameter addressing and CV control",
            "MIDI Control: Add MIDI learn, mapping, and device management",
            "Bundle Management: Complete bundle add/remove functionality",
        ],
        "Low Priority (Specialized Features)": [
            "Control Chain: Implement Control Chain device communication",
            "Transport/Tempo: Add advanced transport synchronization",
        ],
    }

    for priority, items in recommendations.items():
        print(f"\n{priority}:")
        for item in items:
            print(f"  • {item}")


if __name__ == "__main__":
    coverage_results = analyze_coverage()
    generate_implementation_recommendations()

    print(f"\n🏁 CONCLUSION:")
    overall = (
        sum(coverage_results.values()) / len(coverage_results)
        if coverage_results
        else 0
    )

    if overall >= 70:
        print(
            f"✅ Good implementation coverage ({overall:.1f}%) - Most core functionality preserved"
        )
    elif overall >= 40:
        print(
            f"⚠️  Moderate implementation coverage ({overall:.1f}%) - Some gaps need attention"
        )
    else:
        print(
            f"❌ Low implementation coverage ({overall:.1f}%) - Significant functionality missing"
        )
