"""
MOD Legacy Utilities

Legacy components copied from the original MOD codebase for use
in the new microservices architecture. These are frozen copies
to maintain functionality while the original code is archived.

Components:
- session.py: Session management functionality
- settings.py: Configuration and settings
- control_chain.py: Control Chain hardware communication
- hmi.py: HMI (Human Machine Interface) functions

Note: These are compatibility copies. New development should
use the modernized microservices instead of these legacy modules.
"""

import os

# Import functions from the original __init__.py that are needed by utilities
import sys

# Import the original functions from mod_ui_original
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "mod_ui_original")
)

try:
    # Import commonly used functions from the original __init__.py
    from __init__ import (
        check_environment,
        get_hardware_actuators,
        get_hardware_descriptor,
        get_unique_name,
        json_handler,
        jsoncall,
        normalize_for_hw,
        safe_json_load,
        symbolify,
    )

    # Make them available for import
    __all__ = [
        "get_unique_name",
        "get_hardware_descriptor",
        "get_hardware_actuators",
        "safe_json_load",
        "check_environment",
        "normalize_for_hw",
        "symbolify",
        "jsoncall",
        "json_handler",
    ]

except ImportError as e:
    import warnings

    warnings.warn(f"Could not import original MOD functions: {e}", ImportWarning)

    # Provide fallback implementations
    def get_unique_name(name, names):
        """Fallback implementation"""
        return name if name not in names else f"{name}_copy"

    def get_hardware_descriptor():
        """Fallback implementation"""
        return {}

    def get_hardware_actuators():
        """Fallback implementation"""
        return []

    def safe_json_load(path, objtype):
        """Fallback implementation"""
        return objtype()

    def check_environment():
        """Fallback implementation"""
        return True


# Mark this as a legacy/archive package
__version__ = "legacy"
__status__ = "archived"
__migration_target__ = "src/mod_ui/services/"
