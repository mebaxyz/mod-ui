"""
Pages Router

Handles HTML page rendering for the MOD UI web interface.
"""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..utils.templates import (
    apply_template_context,
    get_template_context_index,
    get_template_context_pedalboard,
    get_template_context_settings,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["pages"])

# Get HTML directory from environment
HTML_DIR = os.environ.get("MOD_HTML_DIR", "/app/html")


@router.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serve the main index page with proper template context

    Renders the main MOD UI interface page with all necessary
    template variables for proper frontend initialization.
    """
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
                </ul>
                
                <h2>WebSocket:</h2>
                <p>WebSocket endpoint available at <code>ws://localhost:8888/websocket</code></p>
            </body>
            </html>
            """
            )
    except Exception as e:
        logger.error(f"Error serving root page: {e}")
        return HTMLResponse(content=f"<h1>MOD UI</h1><p>Error: {e}</p>")


@router.get("/pedalboard", response_class=HTMLResponse)
async def pedalboard_page(bundlepath: str = ""):
    """
    Serve the pedalboard page with proper template context

    Renders the pedalboard interface page where users can
    create and edit their effect pedalboards.
    """
    try:
        pedalboard_path = os.path.join(HTML_DIR, "pedalboard.html")
        if os.path.exists(pedalboard_path):
            with open(pedalboard_path, "r") as f:
                content = f.read()

            # Get template context matching original logic
            context = get_template_context_pedalboard(bundlepath)
            content = apply_template_context(content, context)

            # Apply additional template replacements that weren't in context
            replacements = {
                "{{hardware_label}}": "MOD Device",
                "{{uri}}": "http://localhost:8888",
                "{{cloud_url}}": "https://cloud.moddevices.com",
                "{{cloud_labs_url}}": "https://cloud.moddevices.com/labs",
                "{{plugins_url}}": "https://cloud.moddevices.com/plugins",
                "{{pedalboards_url}}": "https://cloud.moddevices.com/pedalboards",
                "{{pedalboards_labs_url}}": "https://cloud.moddevices.com/labs/pedalboards",
                "{{controlchain_url}}": "https://wiki.moddevices.com/wiki/Control_Chain",
                "{{lv2_plugin_dir}}": "/app/lv2",
                "{{bin_compat}}": "x86_64",
                "{{platform}}": "linux",
                "{{sampleRate}}": "48000",
                "{{bufferSize}}": "256",
                "{{using_desktop}}": "false",
                "{{using_mod}}": "true",
                "{{factory_pedalboards}}": "true",
                "{{hardware_profile}}": "e30=",
                "{{favorites}}": "[]",
                "{{preferences}}": "{}",
                "{{addressing_pages}}": "[]",
                "{{bundlepath}}": "",
                "{{title}}": "",
                "{{codec_truebypass}}": "true",
                "{{user_name}}": "",
                "{{user_email}}": "",
                "{{titleblend}}": "",
                "{{fulltitle}}": "MOD UI",
                "{{dev_api_class}}": "",
            }

            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)

            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>Pedalboard</h1><p>Pedalboard interface coming soon...</p>"
            )
    except Exception as e:
        logger.error(f"Error serving pedalboard page: {e}")
        return HTMLResponse(content=f"<h1>Pedalboard</h1><p>Error: {e}</p>")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """
    Serve the settings page with proper template context

    Renders the settings interface page where users can
    configure system preferences and user settings.
    """
    try:
        settings_path = os.path.join(HTML_DIR, "settings.html")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                content = f.read()

            # Get template context matching original logic
            context = get_template_context_settings()
            content = apply_template_context(content, context)

            # Apply additional template replacements
            replacements = {
                "{{cloud_url}}": "https://cloud.moddevices.com",
                "{{cloud_labs_url}}": "https://cloud.moddevices.com/labs",
                "{{plugins_url}}": "https://cloud.moddevices.com/plugins",
                "{{pedalboards_url}}": "https://cloud.moddevices.com/pedalboards",
                "{{pedalboards_labs_url}}": "https://cloud.moddevices.com/labs/pedalboards",
                "{{controlchain_url}}": "https://wiki.moddevices.com/wiki/Control_Chain",
                "{{lv2_plugin_dir}}": "/app/lv2",
                "{{bin_compat}}": "x86_64",
                "{{platform}}": "linux",
                "{{sampleRate}}": "48000",
            }

            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)

            return HTMLResponse(content=content)
        else:
            return HTMLResponse(
                content="<h1>Settings</h1><p>Settings interface coming soon...</p>"
            )
    except Exception as e:
        logger.error(f"Error serving settings page: {e}")
        return HTMLResponse(content=f"<h1>Settings</h1><p>Error: {e}</p>")


@router.get("/test-websocket", response_class=HTMLResponse)
async def websocket_test():
    """
    WebSocket test page

    Simple test page for debugging WebSocket connections.
    """
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
