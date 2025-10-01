#!/usr/bin/env python3
"""
Comprehensive comparison between original MOD UI (host.py) and new audio_processing service
to ensure all original methods are preserved in the new implementation.
"""

import ast
import os
import re
from typing import Dict, List, Set


def extract_methods_from_file(filepath: str) -> Set[str]:
    """Extract all method names from a Python file"""
    methods = set()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Use regex to find def statements (more reliable for large files)
        pattern = r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
        matches = re.findall(pattern, content, re.MULTILINE)
        methods.update(matches)

    except Exception as e:
        print(f"Error reading {filepath}: {e}")

    return methods


def extract_handler_methods_from_service() -> Set[str]:
    """Extract handler methods from the new audio processing service"""
    service_files = [
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/main.py",
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/modhost_bridge.py",
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/plugin_manager.py",
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui/services/audio_processing/session_manager.py",
    ]

    all_methods = set()
    for filepath in service_files:
        if os.path.exists(filepath):
            methods = extract_methods_from_file(filepath)
            all_methods.update(methods)
            print(f"Found {len(methods)} methods in {os.path.basename(filepath)}")

    return all_methods


def analyze_original_host_functionality():
    """Analyze the original host.py to categorize functionality"""
    original_host = "/home/nicolas/project/madeline/mod-ui/src/mod_ui_original/host.py"

    if not os.path.exists(original_host):
        print(f"❌ Original host.py not found at {original_host}")
        return set(), {}

    methods = extract_methods_from_file(original_host)
    print(f"Found {len(methods)} methods in original host.py")

    # Categorize methods by functionality
    categories = {
        "Plugin Management": [],
        "Parameter Control": [],
        "Pedalboard Management": [],
        "Connection Management": [],
        "HMI/Hardware": [],
        "JACK/Audio": [],
        "MIDI": [],
        "Addressing": [],
        "Session Management": [],
        "Utility/Internal": [],
    }

    for method in methods:
        if any(x in method.lower() for x in ["plugin", "add_", "remove_", "bypass"]):
            categories["Plugin Management"].append(method)
        elif any(x in method.lower() for x in ["param", "patch", "value"]):
            categories["Parameter Control"].append(method)
        elif any(x in method.lower() for x in ["pedalboard", "pb", "board"]):
            categories["Pedalboard Management"].append(method)
        elif any(x in method.lower() for x in ["connect", "port", "disconnect"]):
            categories["Connection Management"].append(method)
        elif any(x in method.lower() for x in ["hmi", "hw_", "hardware", "footswitch"]):
            categories["HMI/Hardware"].append(method)
        elif any(x in method.lower() for x in ["jack", "bufsize", "audio"]):
            categories["JACK/Audio"].append(method)
        elif any(x in method.lower() for x in ["midi"]):
            categories["MIDI"].append(method)
        elif any(x in method.lower() for x in ["addr", "addressing"]):
            categories["Addressing"].append(method)
        elif any(x in method.lower() for x in ["session", "start_", "end_", "init_"]):
            categories["Session Management"].append(method)
        else:
            categories["Utility/Internal"].append(method)

    return methods, categories


def check_webserver_endpoints():
    """Check webserver.py for HTTP endpoints that need to be preserved"""
    webserver_file = (
        "/home/nicolas/project/madeline/mod-ui/src/mod_ui_original/webserver.py"
    )

    if not os.path.exists(webserver_file):
        print(f"❌ Original webserver.py not found")
        return []

    endpoints = []
    try:
        with open(webserver_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Find HTTP route decorators
        route_pattern = r'@web\.route\([\'"]([^\'"]+)[\'"]'
        matches = re.findall(route_pattern, content)
        endpoints.extend(matches)

        # Find tornado handlers
        handler_pattern = r"class\s+([a-zA-Z_][a-zA-Z0-9_]*Handler)"
        handler_matches = re.findall(handler_pattern, content)
        endpoints.extend([f"{h} (Handler)" for h in handler_matches])

    except Exception as e:
        print(f"Error reading webserver.py: {e}")

    return endpoints


def compare_implementations():
    """Main comparison function"""
    print("🔍 COMPREHENSIVE MOD UI IMPLEMENTATION COMPARISON")
    print("=" * 80)

    # Get original host methods
    original_methods, categories = analyze_original_host_functionality()

    # Get new service methods
    new_methods = extract_handler_methods_from_service()

    # Get webserver endpoints
    endpoints = check_webserver_endpoints()

    print(f"\n📊 SUMMARY:")
    print(f"• Original host.py methods: {len(original_methods)}")
    print(f"• New service methods: {len(new_methods)}")
    print(f"• Original webserver endpoints: {len(endpoints)}")

    print(f"\n📋 ORIGINAL HOST.PY FUNCTIONALITY BY CATEGORY:")
    total_categorized = 0
    for category, methods in categories.items():
        if methods:
            print(f"\n{category} ({len(methods)} methods):")
            total_categorized += len(methods)
            for method in sorted(methods)[:10]:  # Show first 10
                print(f"  • {method}")
            if len(methods) > 10:
                print(f"  ... and {len(methods) - 10} more")

    # Check for critical missing methods
    critical_methods = [
        "add_plugin",
        "remove_plugin",
        "bypass",
        "param_set",
        "param_get",
        "connect",
        "disconnect",
        "reset",
        "mute",
        "unmute",
        "add_bundle",
        "remove_bundle",
        "patch_set",
        "patch_get",
    ]

    print(f"\n🎯 CRITICAL METHOD COVERAGE CHECK:")
    for method in critical_methods:
        if method in original_methods:
            # Check if equivalent exists in new service
            new_equivalents = [m for m in new_methods if method in m.lower()]
            if new_equivalents:
                print(f"  ✅ {method} -> {', '.join(new_equivalents[:3])}")
            else:
                print(f"  ❌ {method} -> NOT FOUND")
        else:
            print(f"  ⚠️  {method} -> NOT IN ORIGINAL")

    print(f"\n📈 IMPLEMENTATION STATUS:")
    covered_functionality = 0
    total_functionality = len(categories)

    for category, methods in categories.items():
        if not methods:
            continue

        # Check if this category is covered in new implementation
        category_keywords = category.lower().split()
        found_methods = []

        for keyword in category_keywords:
            found_methods.extend([m for m in new_methods if keyword in m.lower()])

        if found_methods:
            covered_functionality += 1
            print(
                f"  ✅ {category}: Covered ({len(set(found_methods))} related methods)"
            )
        else:
            print(f"  ❌ {category}: Missing coverage")

    coverage_percentage = (covered_functionality / total_functionality) * 100
    print(
        f"\n🎉 OVERALL COVERAGE: {coverage_percentage:.1f}% ({covered_functionality}/{total_functionality} categories)"
    )

    return {
        "original_methods": original_methods,
        "new_methods": new_methods,
        "categories": categories,
        "endpoints": endpoints,
        "coverage": coverage_percentage,
    }


if __name__ == "__main__":
    result = compare_implementations()
