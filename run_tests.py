#!/usr/bin/env python3
"""
Test runner script for WebSocket Gateway Service
"""

import argparse
import os
import subprocess
import sys


def main():
    """Run tests with various options"""

    parser = argparse.ArgumentParser(description="Run WebSocket Gateway tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", help="Run specific test file")
    parser.add_argument("--pattern", help="Run tests matching pattern")

    args = parser.parse_args()

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "src")

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])

    if args.verbose:
        cmd.append("-v")

    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])

    if args.file:
        # Check if file exists in websocket_gateway tests first
        ws_gateway_test_file = os.path.join(
            "src", "mod_ui", "services", "websocket_gateway", "tests", args.file
        )
        root_test_file = os.path.join("tests", args.file)
        if os.path.exists(ws_gateway_test_file):
            cmd.append(ws_gateway_test_file)
        elif os.path.exists(root_test_file):
            cmd.append(root_test_file)
        else:
            print(f"Test file {args.file} not found in either location")
            sys.exit(1)
    elif args.pattern:
        cmd.extend(["-k", args.pattern])
    else:
        # Run tests from both locations
        cmd.extend(["tests", "src/mod_ui/services/websocket_gateway/tests"])

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {os.getcwd()}")

    # Run tests
    try:
        result = subprocess.run(cmd, env=env, cwd=os.path.dirname(__file__))
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
