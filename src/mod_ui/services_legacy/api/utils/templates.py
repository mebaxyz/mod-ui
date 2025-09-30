"""
Template Utilities

Template context generation and processing utilities for MOD UI pages.
"""

import html
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Import MOD utilities
try:
    from mod_ui.utils.mod_legacy import (
        check_environment,
        get_hardware_descriptor,
        safe_json_load,
    )
    from mod_ui.utils.mod_legacy.settings import (
        API_KEY,
        CLOUD_HTTP_ADDRESS,
        CLOUD_LABS_HTTP_ADDRESS,
        CONTROLCHAIN_HTTP_ADDRESS,
        DEFAULT_ICON_TEMPLATE,
        DEFAULT_PEDALBOARD,
        DEFAULT_SETTINGS_TEMPLATE,
        DESKTOP,
        DEV_API,
        DEV_ENVIRONMENT,
        DEV_HMI,
        DEV_HOST,
        DEVICE_KEY,
        DEVICE_TAG,
        DEVICE_UID,
        FAVORITES_JSON_FILE,
        IMAGE_VERSION,
        LV2_PLUGIN_DIR,
        PEDALBOARDS_HTTP_ADDRESS,
        PEDALBOARDS_LABS_HTTP_ADDRESS,
        PLUGINS_HTTP_ADDRESS,
        PREFERENCES_JSON_FILE,
        UNTITLED_PEDALBOARD_NAME,
        USER_ID_JSON_FILE,
    )

    # Try to import modtools utilities
    try:
        from mod_ui.utils.modtools.utils import (
            get_jack_buffer_size,
            get_jack_sample_rate,
        )

        MODTOOLS_AVAILABLE = True
    except ImportError:
        MODTOOLS_AVAILABLE = False

        def get_jack_buffer_size():
            return 512

        def get_jack_sample_rate():
            return 44100

    MOD_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MOD utilities import failed: {e}")
    MOD_UTILS_AVAILABLE = False

    # Fallback implementations
    def safe_json_load(filepath, default_type):
        """Placeholder for safe JSON load"""
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except:
            pass
        return default_type()

    def get_hardware_descriptor():
        return {}

    def get_jack_buffer_size():
        return 256

    def get_jack_sample_rate():
        return 48000

    # Mock settings
    CLOUD_HTTP_ADDRESS = "https://cloud.moddevices.com"
    CLOUD_LABS_HTTP_ADDRESS = "https://cloud.moddevices.com/labs"
    PLUGINS_HTTP_ADDRESS = "https://cloud.moddevices.com/plugins"
    PEDALBOARDS_HTTP_ADDRESS = "https://cloud.moddevices.com/pedalboards"
    PEDALBOARDS_LABS_HTTP_ADDRESS = "https://cloud.moddevices.com/labs/pedalboards"
    CONTROLCHAIN_HTTP_ADDRESS = "https://wiki.moddevices.com/wiki/Control_Chain"
    IMAGE_VERSION = "1.0.0"
    UNTITLED_PEDALBOARD_NAME = "Untitled"
    LV2_PLUGIN_DIR = "/app/lv2"
    DEFAULT_PEDALBOARD = ""
    FAVORITES_JSON_FILE = "/app/data/favorites.json"
    PREFERENCES_JSON_FILE = "/app/data/preferences.json"
    USER_ID_JSON_FILE = "/app/data/user_id.json"
    DEFAULT_ICON_TEMPLATE = ""
    DEFAULT_SETTINGS_TEMPLATE = ""


def mod_squeeze(content: str) -> str:
    """
    Escape content for JavaScript string literals
    This replaces the original mod_squeeze function from webserver.py
    """
    # Replace backslashes first to avoid double escaping
    content = content.replace("\\", "\\\\")
    # Escape single quotes for JavaScript strings
    content = content.replace("'", "\\'")
    # Replace newlines with \\n for JavaScript
    content = content.replace("\n", "\\n")
    content = content.replace("\r", "\\r")
    # Replace tabs
    content = content.replace("\t", "\\t")
    return content


def get_template_context_index() -> Dict[str, Any]:
    """Generate template context for index page matching original TemplateHandler.index()"""
    try:
        # Build basic context even if MOD utilities are not available
        import time

        # Get version string (matches original get_version logic)
        version_arg = "1"
        if MOD_UTILS_AVAILABLE and IMAGE_VERSION is not None and len(IMAGE_VERSION) > 1:
            # strip initial 'v' from version if present
            version_arg = (
                IMAGE_VERSION[1:] if IMAGE_VERSION[0] == "v" else IMAGE_VERSION
            )
        else:
            # Use timestamp as fallback
            version_arg = str(int(time.time()))

        # Basic context that always works
        basic_context = {
            "version": version_arg,
            "cloud_url": (
                CLOUD_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://cloud.moddevices.com"
            ),
            "cloud_labs_url": (
                CLOUD_LABS_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://cloud.moddevices.com/labs"
            ),
            "plugins_url": (
                PLUGINS_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://cloud.moddevices.com/plugins"
            ),
            "pedalboards_url": (
                PEDALBOARDS_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://cloud.moddevices.com/pedalboards"
            ),
            "pedalboards_labs_url": (
                PEDALBOARDS_LABS_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://cloud.moddevices.com/labs/pedalboards"
            ),
            "controlchain_url": (
                CONTROLCHAIN_HTTP_ADDRESS
                if MOD_UTILS_AVAILABLE
                else "https://wiki.moddevices.com/wiki/Control_Chain"
            ),
            "using_desktop": "true" if (MOD_UTILS_AVAILABLE and DESKTOP) else "false",
            "using_mod": "false",  # Default to false for now
            "dev_api_class": "dev_api" if (MOD_UTILS_AVAILABLE and DEV_API) else "",
            "default_icon_template": "",
            "default_settings_template": "",
            "default_pedalboard": "",
            "hardware_profile": "e30=",  # base64 encoded empty dict
            "bin_compat": "Unknown",
            "codec_truebypass": "false",
            "factory_pedalboards": False,
            "platform": "Unknown",
            "addressing_pages": 0,
            "lv2_plugin_dir": "/app/lv2",
            "bundlepath": "",
            "title": "",
            "size": "[]",
            "fulltitle": "Untitled",
            "titleblend": "blend",
            "user_name": "",
            "user_email": "",
            "favorites": "[]",
            "preferences": "{}",
            "bufferSize": 256,
            "sampleRate": 48000,
        }

        if not MOD_UTILS_AVAILABLE:
            logger.warning("Using basic template context - MOD utilities not available")
            return basic_context

        # Enhanced context with MOD utilities
        hwdesc = get_hardware_descriptor()

        # Read default templates
        default_icon_template = ""
        default_settings_template = ""
        try:
            if DEFAULT_ICON_TEMPLATE and os.path.exists(DEFAULT_ICON_TEMPLATE):
                with open(DEFAULT_ICON_TEMPLATE, "r") as fh:
                    content = fh.read()
                    # Properly escape for JavaScript string literals and apply mod_squeeze
                    default_icon_template = (
                        mod_squeeze(content)
                        .replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                    )
            if DEFAULT_SETTINGS_TEMPLATE and os.path.exists(DEFAULT_SETTINGS_TEMPLATE):
                with open(DEFAULT_SETTINGS_TEMPLATE, "r") as fh:
                    content = fh.read()
                    # Properly escape for JavaScript string literals and apply mod_squeeze
                    default_settings_template = (
                        mod_squeeze(content)
                        .replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                    )
        except Exception as e:
            logger.warning(f"Could not load default templates: {e}")

        # Load real MOD data
        import base64

        # Load favorites
        favorites = safe_json_load(FAVORITES_JSON_FILE, list)

        # Load preferences
        preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)

        # Load user ID
        user_id = safe_json_load(USER_ID_JSON_FILE, dict)
        user_name = user_id.get("name", "")
        user_email = user_id.get("email", "")

        # Get pedalboard info (placeholder for SESSION integration)
        pbname = ""  # TODO: SESSION.host.pedalboard_name
        prname = ""  # TODO: SESSION.host.snapshot_name()
        fullpbname = pbname or UNTITLED_PEDALBOARD_NAME
        if prname:
            fullpbname += " - " + prname

        # Get hardware profile
        hardware_profile = "e30="  # base64 encoded empty dict
        try:
            # TODO: Integrate with SESSION.get_hardware_actuators()
            hardware_profile = base64.b64encode(json.dumps({}).encode("utf-8")).decode(
                "utf-8"
            )
        except:
            pass

        # Update basic context with MOD data
        context = basic_context.copy()
        context.update(
            {
                "default_icon_template": default_icon_template,
                "default_settings_template": default_settings_template,
                "default_pedalboard": (
                    mod_squeeze(DEFAULT_PEDALBOARD) if DEFAULT_PEDALBOARD else ""
                ),
                "hardware_profile": hardware_profile,
                "bin_compat": hwdesc.get("bin-compat", "Unknown"),
                "codec_truebypass": (
                    "true" if hwdesc.get("codec_truebypass", False) else "false"
                ),
                "factory_pedalboards": hwdesc.get("factory_pedalboards", False),
                "platform": hwdesc.get("platform", "Unknown"),
                "addressing_pages": int(hwdesc.get("addressing_pages", 0)),
                "lv2_plugin_dir": mod_squeeze(LV2_PLUGIN_DIR),
                "bundlepath": "",  # TODO: mod_squeeze(SESSION.host.pedalboard_path)
                "title": mod_squeeze(user_name) if user_name else mod_squeeze(pbname),
                "size": "[]",  # TODO: json.dumps(SESSION.host.pedalboard_size)
                "fulltitle": html.escape(fullpbname),
                "titleblend": (
                    "" if pbname else "blend"
                ),  # TODO: '' if SESSION.host.pedalboard_name else 'blend'
                "dev_api_class": "dev_api" if DEV_API else "",
                "using_desktop": "true" if DESKTOP else "false",
                "using_mod": (
                    "true"
                    if DEVICE_KEY and hwdesc.get("platform", None) is not None
                    else "false"
                ),
                "user_name": mod_squeeze(user_name),
                "user_email": mod_squeeze(user_email),
                "favorites": json.dumps(favorites),
                "preferences": json.dumps(preferences),
                "bufferSize": get_jack_buffer_size(),
                "sampleRate": get_jack_sample_rate(),
            }
        )
        return context
    except Exception as e:
        logger.error(f"Error generating index template context: {e}")
        # Return basic context as fallback
        import time

        return {
            "version": str(int(time.time())),
            "cloud_url": "https://cloud.moddevices.com",
            "using_desktop": "false",
            "using_mod": "false",
            "dev_api_class": "",
            "default_icon_template": "",
            "default_settings_template": "",
            "default_pedalboard": "",
            "hardware_profile": "e30=",
            "bin_compat": "Unknown",
            "codec_truebypass": "false",
            "factory_pedalboards": False,
            "platform": "Unknown",
            "addressing_pages": 0,
            "lv2_plugin_dir": "/app/lv2",
            "bundlepath": "",
            "title": "",
            "size": "[]",
            "fulltitle": "Untitled",
            "titleblend": "blend",
            "user_name": "",
            "user_email": "",
            "favorites": "[]",
            "preferences": "{}",
            "bufferSize": 256,
            "sampleRate": 48000,
        }


def get_template_context_pedalboard(bundlepath: str = "") -> Dict[str, Any]:
    """Generate template context for pedalboard page matching original TemplateHandler.pedalboard()"""
    try:
        if not MOD_UTILS_AVAILABLE:
            return {}

        # Read default templates (matching original exactly)
        default_icon_template = ""
        default_settings_template = ""
        try:
            if DEFAULT_ICON_TEMPLATE and os.path.exists(DEFAULT_ICON_TEMPLATE):
                with open(DEFAULT_ICON_TEMPLATE, "r") as fh:
                    content = fh.read()
                    # Apply mod_squeeze first, then escape for JavaScript
                    default_icon_template = (
                        mod_squeeze(content)
                        .replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                    )
            if DEFAULT_SETTINGS_TEMPLATE and os.path.exists(DEFAULT_SETTINGS_TEMPLATE):
                with open(DEFAULT_SETTINGS_TEMPLATE, "r") as fh:
                    content = fh.read()
                    # Apply mod_squeeze first, then escape for JavaScript
                    default_settings_template = (
                        mod_squeeze(content)
                        .replace("\\", "\\\\")
                        .replace("'", "\\'")
                        .replace("\n", "\\n")
                        .replace("\r", "\\r")
                    )
        except Exception as e:
            logger.warning(f"Could not load default templates: {e}")

        # Get pedalboard info (placeholder for now)
        import base64

        pedalboard = {
            "height": 0,
            "width": 0,
            "title": "",
            "connections": [],
            "plugins": [],
            "hardware": {},
        }

        context = {
            "default_icon_template": default_icon_template,
            "default_settings_template": default_settings_template,
            "pedalboard": base64.b64encode(
                json.dumps(pedalboard).encode("utf-8")
            ).decode("utf-8"),
        }
        return context
    except Exception as e:
        logger.error(f"Error generating pedalboard template context: {e}")
        return {}


def get_template_context_settings() -> Dict[str, Any]:
    """Generate template context for settings page matching original TemplateHandler.settings()"""
    try:
        if not MOD_UTILS_AVAILABLE:
            return {}

        # Get hardware descriptor
        hwdesc = get_hardware_descriptor()

        # Load real preferences data
        preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)

        # Load user ID
        user_id = safe_json_load(USER_ID_JSON_FILE, dict)
        user_name = user_id.get("name", "")
        user_email = user_id.get("email", "")

        context = {
            "cloud_url": CLOUD_HTTP_ADDRESS,
            "controlchain_url": CONTROLCHAIN_HTTP_ADDRESS,
            "version": IMAGE_VERSION or "1.0.0",
            "hmi_eeprom": "true" if hwdesc.get("hmi_eeprom", False) else "false",
            "preferences": json.dumps(preferences),
            "bufferSize": str(get_jack_buffer_size()),
            "sampleRate": str(int(get_jack_sample_rate())),
        }
        return context
    except Exception as e:
        logger.error(f"Error generating settings template context: {e}")
        return {}


def apply_template_context(content: str, context: Dict[str, Any]) -> str:
    """Apply template context to content, replacing {{variables}} and removing Tornado syntax"""
    # Replace template variables
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, str(value))

    # Remove Tornado template syntax
    content = content.replace("{% autoescape None %}", "")
    content = content.replace("{% end %}", "")
    content = content.replace(
        "{% if using_desktop == 'true' or using_mod == 'true' %}", ""
    )
    content = content.replace("{% if using_desktop == 'true' %}", "")
    content = content.replace("{% else %}", "")
    content = content.replace("{% endif %}", "")
    content = content.replace("{% if factory_pedalboards %}", "")

    return content
