"""
MOD UI FastAPI Application

Modern FastAPI-based implementation of the MOD UI web interface.
This replaces the legacy Tornado-based webserver with a modern async framework.
"""

import html
import json
import logging
import os

# Import legacy MOD components
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Basic settings (avoid importing complex modules initially)
HTML_DIR = os.environ.get("MOD_HTML_DIR", "/app/html")
DEVICE_WEBSERVER_PORT = int(os.environ.get("MOD_PORT", 8888))
LOG = int(os.environ.get("MOD_LOG", 1))
DESKTOP = os.environ.get("MOD_DESKTOP", "0") == "1"
FAVORITES_JSON_FILE = os.environ.get("MOD_FAVORITES_FILE", "/app/data/favorites.json")
DEFAULT_PEDALBOARD = os.environ.get("MOD_DEFAULT_PEDALBOARD", "/app/default.pedalboard")
IMAGE_VERSION = os.environ.get("MOD_VERSION", "1.0.0")

# Configure logging first
logging.basicConfig(level=(logging.DEBUG if LOG else logging.WARNING))
logger = logging.getLogger(__name__)


# Local implementation of mod_squeeze to avoid Tornado import issues
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


# Import MOD utilities step by step
MOD_UTILS_AVAILABLE = False
try:
    # First try to import basic MOD modules
    from mod import check_environment, safe_json_load

    logger.info("Successfully imported basic MOD modules")

    # Then try to import modtools (which loads the C library)
    from modtools.utils import (
        get_all_plugins,
        get_non_cached_plugin_info,
        get_plugin_info,
        get_plugin_list,
    )
    from modtools.utils import init as lv2_init

    logger.info("Successfully imported MOD utilities with C library")
    MOD_UTILS_AVAILABLE = True

except ImportError as e:
    logger.warning(f"MOD utilities import failed: {e}")
    MOD_UTILS_AVAILABLE = False
except Exception as e:
    logger.error(f"Unexpected error loading MOD utilities: {e}")
    MOD_UTILS_AVAILABLE = False

# Add fallback implementations if MOD utilities not available
if not MOD_UTILS_AVAILABLE:

    def check_environment():
        """Placeholder for environment check"""
        pass

    def safe_json_load(filepath, default_type):
        """Placeholder for safe JSON load"""
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except:
            pass
        return default_type()

    def lv2_init():
        """Initialize LV2 plugin system"""
        from modtools.utils import init

        init()
        logger.info("LV2 plugin system initialized")

    def get_plugin_list():
        """Placeholder for plugin list"""
        return []

    def get_plugin_info(uri):
        """Placeholder for plugin info"""
        return {"uri": uri, "name": "Plugin", "version": "1.0.0"}


# Try to import SESSION
try:
    from mod.session import SESSION

    logger.info("Successfully imported SESSION")
    SESSION_AVAILABLE = True
except Exception as e:
    logger.warning(f"SESSION not available: {e}")
    SESSION = None
    SESSION_AVAILABLE = False


# Global state
class AppState:
    def __init__(self):
        self.favorites: List[str] = []
        self.websocket_clients: List[WebSocket] = []


app_state = AppState()

# Create FastAPI application
app = FastAPI(
    title="MOD UI API",
    description="Modern FastAPI-based MOD UI web interface",
    version=IMAGE_VERSION or "1.0.0",
    debug=bool(LOG >= 2),
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DESKTOP else ["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory=HTML_DIR)

# Mount static files for CSS, JS, images, etc. at root level
app.mount("/css", StaticFiles(directory=os.path.join(HTML_DIR, "css")), name="css")
# Mount JS library and utility files (templates.js is handled separately)
app.mount(
    "/js/lib", StaticFiles(directory=os.path.join(HTML_DIR, "js", "lib")), name="js_lib"
)
app.mount(
    "/js/utils",
    StaticFiles(directory=os.path.join(HTML_DIR, "js", "utils")),
    name="js_utils",
)
app.mount("/img", StaticFiles(directory=os.path.join(HTML_DIR, "img")), name="img")
app.mount(
    "/fonts", StaticFiles(directory=os.path.join(HTML_DIR, "fonts")), name="fonts"
)
app.mount(
    "/resources",
    StaticFiles(directory=os.path.join(HTML_DIR, "resources")),
    name="resources",
)

# Dynamic templates will be handled by the /js/templates.js endpoint defined later

# Keep the /static mount as fallback for any other static files
app.mount("/static", StaticFiles(directory=HTML_DIR), name="static")


@app.get("/test-websocket", response_class=HTMLResponse)
async def websocket_test():
    """WebSocket test page"""
    return HTMLResponse(
        content="""
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
</head>
<body>
    <h1>WebSocket Test</h1>
    <div id="status">Connecting...</div>
    <div id="messages"></div>
    
    <script>
        const ws = new WebSocket("ws://localhost:8888/websocket");
        const statusDiv = document.getElementById('status');
        const messagesDiv = document.getElementById('messages');
        
        ws.onopen = function(event) {
            statusDiv.innerHTML = "✅ Connected!";
            console.log("WebSocket connected");
        };
        
        ws.onmessage = function(event) {
            messagesDiv.innerHTML += "<p>Received: " + event.data + "</p>";
            console.log("Received:", event.data);
        };
        
        ws.onclose = function(event) {
            statusDiv.innerHTML = "❌ Disconnected (code: " + event.code + ")";
            console.log("WebSocket closed:", event.code, event.reason);
        };
        
        ws.onerror = function(error) {
            statusDiv.innerHTML = "❌ Error occurred";
            console.error("WebSocket error:", error);
        };
        
        // Send a test message after connection
        setTimeout(function() {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send("data_ready 1");
            }
        }, 1000);
    </script>
</body>
</html>
    """
    )


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # Note: websocket.accept() should be called before this method
        self.active_connections.append(websocket)
        app_state.websocket_clients.append(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in app_state.websocket_clients:
            app_state.websocket_clients.remove(websocket)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting MOD UI FastAPI application")

    # Initialize environment and LV2
    check_environment()
    lv2_init()

    # Load favorites
    app_state.favorites = safe_json_load(FAVORITES_JSON_FILE, list)

    # Clean up invalid favorites (skip for now)
    # if len(app_state.favorites) > 0:
    #     uris = get_plugin_list()
    #     app_state.favorites = [uri for uri in app_state.favorites if uri in uris]

    logger.info("MOD UI FastAPI application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down MOD UI FastAPI application")

    # Close all WebSocket connections
    for websocket in manager.active_connections[:]:
        try:
            await websocket.send_text("stop")
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")

    # End session if available
    if SESSION_AVAILABLE and SESSION:
        try:
            SESSION.signal_disconnect()
            logger.info("SESSION disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting SESSION: {e}")

    logger.info("MOD UI FastAPI application shutdown complete")


# Template context functions (matching original webserver.py logic)
def get_template_context_index():
    """Generate template context for index page matching original TemplateHandler.index()"""
    try:
        # Import ALL MOD settings and utilities
        from mod import get_hardware_descriptor
        from mod.settings import (
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
        from modtools.utils import get_jack_buffer_size, get_jack_sample_rate

        # Get hardware descriptor
        hwdesc = get_hardware_descriptor()

        # Read default templates
        default_icon_template = ""
        default_settings_template = ""
        try:
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
        except:
            logger.warning("Could not load default templates")

        # Load real MOD data
        import base64
        import json

        # Load favorites
        favorites = []
        try:
            favorites = safe_json_load(FAVORITES_JSON_FILE, list)
        except:
            pass

        # Load preferences
        preferences = {}
        try:
            from mod.settings import PREFERENCES_JSON_FILE

            preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)
        except:
            pass

        # Load user ID
        user_name = ""
        user_email = ""
        try:
            from mod.settings import USER_ID_JSON_FILE

            user_id = safe_json_load(USER_ID_JSON_FILE, dict)
            user_name = user_id.get("name", "")
            user_email = user_id.get("email", "")
        except:
            pass

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

        # Get version string (matches original get_version logic)
        version_arg = "1"
        if IMAGE_VERSION is not None and len(IMAGE_VERSION) > 1:
            # strip initial 'v' from version if present
            version_arg = (
                IMAGE_VERSION[1:] if IMAGE_VERSION[0] == "v" else IMAGE_VERSION
            )
        else:
            import time

            version_arg = str(int(time.time()))

        # Build context matching original exactly
        context = {
            "default_icon_template": default_icon_template,
            "default_settings_template": default_settings_template,
            "default_pedalboard": (
                mod_squeeze(DEFAULT_PEDALBOARD) if DEFAULT_PEDALBOARD else ""
            ),
            "cloud_url": CLOUD_HTTP_ADDRESS,
            "cloud_labs_url": CLOUD_LABS_HTTP_ADDRESS,
            "plugins_url": PLUGINS_HTTP_ADDRESS,
            "pedalboards_url": PEDALBOARDS_HTTP_ADDRESS,
            "pedalboards_labs_url": PEDALBOARDS_LABS_HTTP_ADDRESS,
            "controlchain_url": CONTROLCHAIN_HTTP_ADDRESS,
            "hardware_profile": hardware_profile,
            "version": version_arg,
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
            "favorites": json.dumps(favorites),  # TODO: json.dumps(gState.favorites)
            "preferences": json.dumps(
                preferences
            ),  # TODO: json.dumps(SESSION.prefs.prefs)
            "bufferSize": get_jack_buffer_size(),
            "sampleRate": get_jack_sample_rate(),
        }
        return context
    except Exception as e:
        logger.error(f"Error generating index template context: {e}")
        return {}


def apply_template_context(content: str, context: dict) -> str:
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


def get_template_context_pedalboard(bundlepath: str = ""):
    """Generate template context for pedalboard page matching original TemplateHandler.pedalboard()"""
    try:
        # Import MOD utilities with ALL settings
        from mod.settings import DEFAULT_ICON_TEMPLATE, DEFAULT_SETTINGS_TEMPLATE

        # Read default templates (matching original exactly)
        default_icon_template = ""
        default_settings_template = ""
        try:
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
        except:
            logger.warning("Could not load default templates")

        # Get pedalboard info (placeholder for now)
        import base64
        import json

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


def get_template_context_settings():
    """Generate template context for settings page matching original TemplateHandler.settings()"""
    try:
        # Import ALL MOD settings and utilities
        import json

        # Using global mod_squeeze function
        from mod import get_hardware_descriptor
        from mod.settings import (
            DESKTOP,
            DEV_API,
            DEVICE_KEY,
            IMAGE_VERSION,
            PREFERENCES_JSON_FILE,
            USER_ID_JSON_FILE,
        )
        from modtools.utils import get_jack_buffer_size, get_jack_sample_rate

        # Define mod_squeeze locally (from original webserver.py)
        def mod_squeeze(text):
            return squeeze(text.replace("\\", "\\\\").replace("'", "\\'"))

        # Using html.escape instead of xhtml_escape

        # Get hardware descriptor
        hwdesc = get_hardware_descriptor()

        # Load real preferences data
        preferences = {}
        try:
            preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)
        except:
            logger.warning("Could not load preferences file")

        # Load user ID
        user_name = ""
        user_email = ""
        try:
            user_id = safe_json_load(USER_ID_JSON_FILE, dict)
            user_name = user_id.get("name", "")
            user_email = user_id.get("email", "")
        except:
            pass

        context = {
            "cloud_url": "https://cloud.moddevices.com",
            "controlchain_url": "https://wiki.moddevices.com/wiki/Control_Chain",
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


# Template rendering endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main index page with proper template context"""
    try:
        index_path = os.path.join(HTML_DIR, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                content = f.read()

            # Get template context matching original logic
            context = get_template_context_index()
            content = apply_template_context(content, context)

            # Add desktop object initialization to prevent undefined errors
            # Insert before the existing desktop initialization
            desktop_fallback = """
<script type="text/javascript">
// Ensure desktop is available for host.js
var desktop = desktop || {
    blockUI: function(enabled) { 
        console.log('Desktop blockUI called:', enabled); 
    },
    ccDeviceUpdateFinished: function() { 
        console.log('Desktop ccDeviceUpdateFinished called'); 
    }
};
</script>
"""
            # Insert the fallback before the first script tag
            content = content.replace(
                '<script type="text/javascript"',
                desktop_fallback + '<script type="text/javascript"',
                1,
            )

            return HTMLResponse(content=content)
        else:
            # Fallback content
            return HTMLResponse(
                content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>MOD UI</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .status { color: green; }
                    .api-list { list-style-type: none; padding: 0; }
                    .api-list li { padding: 5px 0; }
                    .api-list a { color: #0066cc; text-decoration: none; }
                </style>
            </head>
            <body>
                <h1>MOD UI FastAPI</h1>
                <p class="status">✅ Migration in progress - API is functional!</p>
                
                <h2>Available API Endpoints:</h2>
                <ul class="api-list">
                    <li><a href="/ping">/ping</a> - Health check</li>
                    <li><a href="/system/info">/system/info</a> - System information</li>
                    <li><a href="/system/prefs">/system/prefs</a> - System preferences</li>
                    <li><a href="/effect/list">/effect/list</a> - Plugin list</li>
                    <li><a href="/banks">/banks</a> - Banks management</li>
                    <li><a href="/pedalboards/list">/pedalboards/list</a> - Pedalboards</li>
                    <li><a href="/snapshots">/snapshots</a> - Snapshots</li>
                </ul>
                
                <h2>WebSocket:</h2>
                <p>WebSocket endpoint available at <code>ws://localhost:8888/websocket</code></p>
                <p>Supports commands: param_set, patch_get, patch_set, plugin_pos, pb_size, transport-bpm, transport-rolling</p>
            </body>
            </html>
            """
            )
    except Exception as e:
        logger.error(f"Error serving root page: {e}")
        return HTMLResponse(content=f"<h1>MOD UI</h1><p>Error: {e}</p>")


@app.get("/pedalboard", response_class=HTMLResponse)
async def pedalboard_page(bundlepath: str = ""):
    """Serve the pedalboard page with proper template context"""
    try:
        pedalboard_path = os.path.join(HTML_DIR, "pedalboard.html")
        if os.path.exists(pedalboard_path):
            with open(pedalboard_path, "r") as f:
                content = f.read()

            # Get template context matching original logic
            context = get_template_context_pedalboard(bundlepath)
            content = apply_template_context(content, context)
            content = content.replace("{{hardware_label}}", "MOD Device")
            content = content.replace("{{uri}}", "http://localhost:8888")
            content = content.replace("{{cloud_url}}", "https://cloud.moddevices.com")
            content = content.replace(
                "{{cloud_labs_url}}", "https://cloud.moddevices.com/labs"
            )
            content = content.replace(
                "{{plugins_url}}", "https://cloud.moddevices.com/plugins"
            )
            content = content.replace(
                "{{pedalboards_url}}", "https://cloud.moddevices.com/pedalboards"
            )
            content = content.replace(
                "{{pedalboards_labs_url}}",
                "https://cloud.moddevices.com/labs/pedalboards",
            )
            content = content.replace(
                "{{controlchain_url}}", "https://wiki.moddevices.com/wiki/Control_Chain"
            )
            content = content.replace("{{lv2_plugin_dir}}", "/app/lv2")
            content = content.replace("{{bin_compat}}", "x86_64")
            content = content.replace("{{platform}}", "linux")
            content = content.replace("{{sampleRate}}", "48000")
            content = content.replace("{{bufferSize}}", "256")
            content = content.replace("{{using_desktop}}", "false")
            content = content.replace("{{using_mod}}", "true")
            content = content.replace("{{factory_pedalboards}}", "true")
            content = content.replace("{{hardware_profile}}", "e30=")
            content = content.replace("{{default_icon_template}}", "")
            content = content.replace("{{default_settings_template}}", "")
            content = content.replace("{{default_pedalboard}}", "")
            content = content.replace("{{favorites}}", "[]")
            content = content.replace("{{preferences}}", "{}")
            content = content.replace("{{addressing_pages}}", "[]")
            content = content.replace("{{bundlepath}}", "")
            content = content.replace("{{title}}", "")
            content = content.replace("{{codec_truebypass}}", "true")
            content = content.replace("{{user_name}}", "")
            content = content.replace("{{user_email}}", "")
            content = content.replace("{{titleblend}}", "")
            content = content.replace("{{fulltitle}}", "MOD UI")
            content = content.replace("{{dev_api_class}}", "")
            content = content.replace("{% autoescape None %}", "")
            content = content.replace("{% end %}", "")
            content = content.replace(
                "{% if using_desktop == 'true' or using_mod == 'true' %}", ""
            )
            content = content.replace("{% if using_desktop == 'true' %}", "")
            content = content.replace("{% else %}", "")
            content = content.replace("{% endif %}", "")
            content = content.replace("{% if factory_pedalboards %}", "")
            content = content.replace(
                "{% if using_desktop == 'true' or using_mod == 'true' %}", ""
            )
            content = content.replace("{% if using_desktop == 'true' %}", "")
            content = content.replace("{% else %}", "")
            content = content.replace("{% endif %}", "")
            content = content.replace("{% if factory_pedalboards %}", "")

            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>Pedalboard</h1><p>Pedalboard interface coming soon...</p>"
            )
    except Exception as e:
        logger.error(f"Error serving pedalboard page: {e}")
        return HTMLResponse(content=f"<h1>Pedalboard</h1><p>Error: {e}</p>")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """Serve the settings page with proper template context"""
    try:
        settings_path = os.path.join(HTML_DIR, "settings.html")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                content = f.read()

            # Get template context matching original logic
            context = get_template_context_settings()
            content = apply_template_context(content, context)
            content = content.replace("{{cloud_url}}", "https://cloud.moddevices.com")
            content = content.replace(
                "{{cloud_labs_url}}", "https://cloud.moddevices.com/labs"
            )
            content = content.replace(
                "{{plugins_url}}", "https://cloud.moddevices.com/plugins"
            )
            content = content.replace(
                "{{pedalboards_url}}", "https://cloud.moddevices.com/pedalboards"
            )
            content = content.replace(
                "{{pedalboards_labs_url}}",
                "https://cloud.moddevices.com/labs/pedalboards",
            )
            content = content.replace(
                "{{controlchain_url}}", "https://wiki.moddevices.com/wiki/Control_Chain"
            )
            content = content.replace("{{lv2_plugin_dir}}", "/app/lv2")
            content = content.replace("{{bin_compat}}", "x86_64")
            content = content.replace("{{platform}}", "linux")
            content = content.replace("{{sampleRate}}", "48000")
            content = content.replace("{% autoescape None %}", "")
            content = content.replace("{% end %}", "")

            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>Settings</h1><p>Settings interface coming soon...</p>"
            )
    except Exception as e:
        logger.error(f"Error serving settings page: {e}")
        return HTMLResponse(content=f"<h1>Settings</h1><p>Error: {e}</p>")


# System Information
@app.get("/system/info")
async def get_system_info():
    """Get system information and status"""
    return JSONResponse(
        {
            "success": True,
            "data": {
                "version": IMAGE_VERSION or "1.0.0",
                "hardware": "MOD Duo",
                "uptime": 3600,  # TODO: Get actual uptime
                "framework": "FastAPI",
                "migration_status": "in_progress",
            },
        }
    )


# Plugin Management
@app.get("/effect/list")
async def get_plugin_list_endpoint():
    """List all available plugins (matches original EffectList handler)"""
    try:
        # Use get_all_plugins() to get plugin objects with proper structure
        # This matches the original Tornado EffectList handler
        from modtools.utils import get_all_plugins

        plugins = get_all_plugins()
        return JSONResponse(plugins)
    except Exception as e:
        logger.error(f"Error getting plugin list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/effect/get")
async def get_plugin_info_endpoint(uri: str):
    """Get information about a specific plugin"""
    try:
        plugin_data = get_plugin_info(uri)
        return JSONResponse({"success": True, "data": plugin_data})
    except Exception as e:
        logger.error(f"Error getting plugin info for {uri}: {e}")
        raise HTTPException(status_code=404, detail=f"Plugin not found: {uri}")


# Favorites Management
@app.post("/favorites/add")
async def add_favorite(uri: str):
    """Add a plugin to favorites"""
    if uri not in app_state.favorites:
        app_state.favorites.append(uri)
        # TODO: Save to favorites file
    return JSONResponse({"success": True, "message": "Added to favorites"})


@app.post("/favorites/remove")
async def remove_favorite(uri: str):
    """Remove a plugin from favorites"""
    if uri in app_state.favorites:
        app_state.favorites.remove(uri)
        # TODO: Save to favorites file
    return JSONResponse({"success": True, "message": "Removed from favorites"})


# Template loader endpoint (matches original BulkTemplateLoader)
@app.get("/js/templates.js")
async def bulk_template_loader():
    """Load all HTML templates and convert them to JavaScript TEMPLATES object"""
    import os
    import re

    from fastapi.responses import Response

    content = []
    include_dir = os.path.join(HTML_DIR, "include")

    if os.path.exists(include_dir):
        for template_file in os.listdir(include_dir):
            if not re.match(r"^[a-z_]+\.html$", template_file):
                continue

            template_path = os.path.join(include_dir, template_file)
            try:
                with open(template_path, "r", encoding="utf-8") as fh:
                    template_content = fh.read()

                # Use mod_squeeze to escape for JavaScript
                template_name = template_file[:-5]  # Remove .html extension
                escaped_content = mod_squeeze(template_content)
                content.append(f"TEMPLATES['{template_name}'] = '{escaped_content}';\n")

            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")

    javascript_content = "\n".join(content)

    return Response(
        content=javascript_content,
        media_type="text/javascript; charset=UTF-8",
        headers={
            "Cache-Control": "public, max-age=31536000",
            "Expires": "Mon, 31 Dec 2035 12:00:00 GMT",
        },
    )


# Custom JS file handler for other JS files (after templates.js is handled above)
@app.get("/js/{filename}")
async def serve_js_files(filename: str):
    """Serve static JS files (templates.js is handled by the endpoint above)"""
    js_dir = os.path.join(HTML_DIR, "js")
    file_path = os.path.join(js_dir, filename)

    # Security check to prevent directory traversal
    if not os.path.commonpath([js_dir, file_path]) == js_dir:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import FileResponse

    return FileResponse(file_path, media_type="application/javascript")


# WebSocket endpoint
@app.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    logger.info(f"WebSocket connection attempt from {websocket.client}")

    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        await manager.connect(websocket)
    except Exception as e:
        logger.error(f"Error accepting WebSocket connection: {e}")
        await websocket.close(code=1000, reason="Connection error")
        return

    # Notify session about WebSocket connection if available
    if SESSION_AVAILABLE and SESSION:
        try:
            # Note: SESSION.websocket_opened expects Tornado-style callback, we'll adapt this
            logger.debug("WebSocket connected, SESSION available")
        except Exception as e:
            logger.error(f"Error notifying SESSION about WebSocket: {e}")

    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"WebSocket received: {message}")

            # Handle pong messages (keepalive)
            if message == "pong":
                continue

            # Parse command and data
            if " " in message:
                cmd, data = message.split(" ", 1)
            else:
                cmd = message
                data = ""

            # Process WebSocket commands
            await handle_websocket_command(websocket, cmd, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed")
        # Notify session about WebSocket disconnection if available
        if SESSION_AVAILABLE and SESSION:
            try:
                logger.debug("WebSocket disconnected, SESSION available")
            except Exception as e:
                logger.error(f"Error notifying SESSION about WebSocket disconnect: {e}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_websocket_command(websocket: WebSocket, cmd: str, data: str):
    """Handle WebSocket commands from the frontend"""
    try:
        if cmd == "data_ready":
            # Handle data ready acknowledgment
            counter = int(data) if data else 0
            if SESSION_AVAILABLE and SESSION:
                SESSION.ws_data_ready(counter)
            logger.debug(f"Data ready: {counter}")

        elif cmd == "param_set":
            # Handle parameter changes: param_set port value
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                port = parts[0]
                value = float(parts[1])
                if SESSION_AVAILABLE and SESSION:
                    SESSION.ws_parameter_set(port, value, websocket)
                logger.debug(f"Parameter set: {port} = {value}")

        elif cmd == "patch_get":
            # Handle patch get request: patch_get instance uri
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                inst = parts[0]
                uri = parts[1]
                if SESSION_AVAILABLE and SESSION:
                    SESSION.ws_patch_get(inst, uri, websocket)
                logger.debug(f"Patch get: {inst} {uri}")

        elif cmd == "patch_set":
            # Handle patch set: patch_set instance uri type value
            parts = data.split(" ", 3)
            if len(parts) >= 4:
                inst = parts[0]
                uri = parts[1]
                vtype = parts[2]
                value = parts[3]
                if SESSION_AVAILABLE and SESSION:
                    SESSION.ws_patch_set(inst, uri, vtype, value, websocket)
                logger.debug(f"Patch set: {inst} {uri} {vtype} {value}")

        elif cmd == "plugin_pos":
            # Handle plugin position: plugin_pos instance x y
            parts = data.split(" ", 3)
            if len(parts) >= 3:
                inst = parts[0]
                x = float(parts[1])
                y = float(parts[2])
                if SESSION_AVAILABLE and SESSION:
                    SESSION.ws_plugin_position(inst, x, y, websocket)
                logger.debug(f"Plugin position: {inst} ({x}, {y})")

        elif cmd == "pb_size":
            # Handle pedalboard size: pb_size width height
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                width = int(float(parts[0]))
                height = int(float(parts[1]))
                if SESSION_AVAILABLE and SESSION:
                    SESSION.ws_pedalboard_size(width, height)
                logger.debug(f"Pedalboard size: {width}x{height}")

        elif cmd == "transport-bpm":
            # Handle transport BPM changes
            bpm = float(data) if data else 120.0
            if SESSION_AVAILABLE and SESSION:
                # Note: Original uses gen.Task, we'll need to adapt this
                logger.debug(f"Transport BPM: {bpm}")
            else:
                logger.debug(f"Transport BPM: {bpm} (SESSION not available)")

        elif cmd == "transport-rolling":
            # Handle transport start/stop
            rolling = bool(int(data)) if data else False
            if SESSION_AVAILABLE and SESSION:
                logger.debug(f"Transport rolling: {rolling}")
            else:
                logger.debug(f"Transport rolling: {rolling} (SESSION not available)")

        else:
            logger.warning(f"Unknown WebSocket command: {cmd} {data}")
            # Echo back for unknown commands during development
            await websocket.send_text(f"Unknown command: {cmd}")

    except ValueError as e:
        logger.error(f"Error parsing WebSocket command '{cmd} {data}': {e}")
        await websocket.send_text(f"Error: Invalid command format")
    except Exception as e:
        logger.error(f"Error handling WebSocket command '{cmd} {data}': {e}")
        await websocket.send_text(f"Error: {str(e)}")


# Health check endpoint
@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return JSONResponse(
        {
            "success": True,
            "data": {
                "ihm_online": True,
                "ihm_time": 1,
                "timestamp": datetime.now().isoformat(),
            },
        }
    )


# Hello endpoint (for remote monitoring)
@app.get("/hello")
async def hello():
    """Remote monitoring endpoint"""
    return JSONResponse(
        {
            "online": len(manager.active_connections) > 0,
            "version": IMAGE_VERSION or "1.0.0",
            "framework": "FastAPI",
        }
    )


# WebSocket health check endpoint
@app.get("/websocket/health")
async def websocket_health():
    """WebSocket health check endpoint"""
    return JSONResponse(
        {
            "websocket_endpoint": "/websocket",
            "active_connections": len(manager.active_connections),
            "session_available": SESSION_AVAILABLE,
            "status": "ready",
        }
    )


# System Preferences
# Settings management endpoints matching original MOD system
@app.post("/config/set")
async def save_config_value(key: str = Form(...), value: str = Form(...)):
    """Set a single configuration value (matches original SaveSingleConfigValue)"""
    try:
        from mod.settings import PREFERENCES_JSON_FILE

        # Load existing preferences
        preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)

        # Update the value
        preferences[key] = value

        # Ensure data directory exists
        os.makedirs(os.path.dirname(PREFERENCES_JSON_FILE), exist_ok=True)

        # Save preferences atomically
        import tempfile

        temp_path = PREFERENCES_JSON_FILE + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(preferences, f, indent=4)
        os.rename(temp_path, PREFERENCES_JSON_FILE)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error saving config value {key}={value}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/prefs")
async def get_system_preferences():
    """Get system preferences (matches original SystemPreferences)"""
    try:
        # Implement system preferences logic matching original
        ret = {}

        # Bluetooth name
        bluetooth_path = "/data/bluetooth/name"
        if os.path.exists(bluetooth_path):
            try:
                with open(bluetooth_path, "r") as f:
                    ret["bluetooth_name"] = f.read().strip()
            except:
                ret["bluetooth_name"] = None
        else:
            ret["bluetooth_name"] = None

        # File-based flags
        ret["jack_mono_copy"] = os.path.exists("/data/jack-mono-copy")
        ret["jack_sync_mode"] = os.path.exists("/data/jack-sync-mode")
        ret["jack_256_frames"] = os.path.exists("/data/using-256-frames")
        ret["separate_spdif_outs"] = os.path.exists("/data/separate-spdif-outs")

        # Services
        ret["service_mod_peakmeter"] = not os.path.exists("/data/disable-mod-peakmeter")
        ret["service_mod_sdk"] = os.path.exists("/data/enable-mod-sdk")
        ret["service_netmanager"] = not os.path.exists("/data/disable-netmanager")

        # Workarounds
        ret["autorestart_hmi"] = os.path.exists("/data/autorestart-hmi")

        return JSONResponse(ret)
    except Exception as e:
        logger.error(f"Error getting system preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/favorites")
async def get_favorites():
    """Get user favorites list"""
    favorites = safe_json_load(FAVORITES_JSON_FILE, list)
    return JSONResponse(favorites)


@app.post("/favorites/add")
async def add_favorite(uri: str = Form(...)):
    """Add plugin to favorites"""
    try:
        favorites = safe_json_load(FAVORITES_JSON_FILE, list)

        if uri not in favorites:
            favorites.append(uri)

            # Ensure data directory exists
            os.makedirs(os.path.dirname(FAVORITES_JSON_FILE), exist_ok=True)

            # Save favorites atomically
            import tempfile

            temp_path = FAVORITES_JSON_FILE + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(favorites, f)
            os.rename(temp_path, FAVORITES_JSON_FILE)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error adding favorite {uri}: {e}")
        return JSONResponse(False)


@app.post("/favorites/remove")
async def remove_favorite(uri: str = Form(...)):
    """Remove plugin from favorites"""
    try:
        favorites = safe_json_load(FAVORITES_JSON_FILE, list)

        if uri in favorites:
            favorites.remove(uri)

            # Save favorites atomically
            import tempfile

            temp_path = FAVORITES_JSON_FILE + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(favorites, f)
            os.rename(temp_path, FAVORITES_JSON_FILE)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error removing favorite {uri}: {e}")
        return JSONResponse(False)


@app.post("/system/prefs")
async def set_system_preferences(preferences: dict):
    """Set system preferences"""
    try:
        preferences_file = os.environ.get(
            "MOD_PREFERENCES_FILE", "/app/data/preferences.json"
        )

        # Ensure data directory exists
        os.makedirs(os.path.dirname(preferences_file), exist_ok=True)

        # Save preferences
        with open(preferences_file, "w") as f:
            json.dump(preferences, f, indent=2)

        return JSONResponse(
            {"success": True, "message": "Preferences saved successfully"}
        )
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Banks Management (JSON-based, no C library needed)
@app.get("/banks")
async def get_banks():
    """List all available banks"""
    banks_file = os.environ.get("MOD_BANKS_FILE", "/app/data/banks.json")
    banks = safe_json_load(banks_file, list)

    # Default banks if file doesn't exist
    if not banks:
        banks = [{"id": 0, "name": "Default Bank", "pedalboards": []}]

    return JSONResponse({"success": True, "data": {"banks": banks}})


@app.post("/bank/new")
async def create_bank(name: str):
    """Create a new bank"""
    try:
        banks_file = os.environ.get("MOD_BANKS_FILE", "/app/data/banks.json")
        banks = safe_json_load(banks_file, list)

        # Generate new bank ID
        bank_id = max([bank.get("id", 0) for bank in banks], default=0) + 1

        new_bank = {"id": bank_id, "name": name, "pedalboards": []}

        banks.append(new_bank)

        # Save banks
        os.makedirs(os.path.dirname(banks_file), exist_ok=True)
        with open(banks_file, "w") as f:
            json.dump(banks, f, indent=2)

        return JSONResponse({"success": True, "data": new_bank})
    except Exception as e:
        logger.error(f"Error creating bank: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Pedalboard Management (basic JSON operations)
@app.get("/pedalboards/list")
async def list_pedalboards():
    """List available pedalboards"""
    try:
        pedalboards_dir = os.environ.get("MOD_PEDALBOARDS_DIR", "/app/data/pedalboards")
        pedalboards = []

        if os.path.exists(pedalboards_dir):
            for filename in os.listdir(pedalboards_dir):
                if filename.endswith(".ttl"):
                    pedalboard_path = os.path.join(pedalboards_dir, filename)
                    pedalboards.append(
                        {
                            "bundle": filename,
                            "title": filename.replace(".ttl", "")
                            .replace("_", " ")
                            .title(),
                            "version": "1.0.0",
                            "uri": f"file://{pedalboard_path}",
                        }
                    )

        return JSONResponse({"success": True, "data": {"pedalboards": pedalboards}})
    except Exception as e:
        logger.error(f"Error listing pedalboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Snapshots Management
@app.get("/snapshots")
async def get_snapshots():
    """Get available snapshots"""
    snapshots_file = os.environ.get("MOD_SNAPSHOTS_FILE", "/app/data/snapshots.json")
    snapshots = safe_json_load(snapshots_file, list)

    return JSONResponse({"success": True, "data": {"snapshots": snapshots}})


@app.post("/snapshot/save")
async def save_snapshot(name: str = "New Snapshot"):
    """Save current state as snapshot"""
    try:
        snapshots_file = os.environ.get(
            "MOD_SNAPSHOTS_FILE", "/app/data/snapshots.json"
        )
        snapshots = safe_json_load(snapshots_file, list)

        snapshot = {
            "id": len(snapshots),
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "data": {"pedalboard": "current", "parameters": {}, "connections": []},
        }

        snapshots.append(snapshot)

        # Save snapshots
        os.makedirs(os.path.dirname(snapshots_file), exist_ok=True)
        with open(snapshots_file, "w") as f:
            json.dump(snapshots, f, indent=2)

        return JSONResponse({"success": True, "data": snapshot})
    except Exception as e:
        logger.error(f"Error saving snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    port = int(os.environ.get("MOD_PORT", DEVICE_WEBSERVER_PORT))
    host = os.environ.get("MOD_HOST", "127.0.0.1" if DESKTOP else "0.0.0.0")
    debug = bool(os.environ.get("MOD_DEBUG", LOG))

    logger.info(f"Starting MOD UI FastAPI server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
    )
