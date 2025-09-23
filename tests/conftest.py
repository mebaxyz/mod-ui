"""
Root tests conftest.py

Shared fixtures and configuration for tests in the root tests directory.
This is separate from the websocket_gateway service tests.
"""

import os
import sys

import pytest

# Add src to path for all root-level tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
