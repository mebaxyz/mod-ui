"""
Shared Utilities Package

Common utilities and helper functions used across the MOD UI API.
"""

from .app_state import AppState, app_state
from .templates import (
    apply_template_context,
    get_template_context_index,
    get_template_context_pedalboard,
    get_template_context_settings,
    mod_squeeze,
)

__all__ = [
    "mod_squeeze",
    "get_template_context_index",
    "get_template_context_pedalboard",
    "get_template_context_settings",
    "apply_template_context",
    "app_state",
    "AppState",
]
