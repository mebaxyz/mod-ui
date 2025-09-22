"""
Static Files Router

Handles static file serving and template loading for the MOD UI.
"""

import logging
import os
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from ..utils.templates import mod_squeeze

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["static"])

# Get HTML directory from environment
HTML_DIR = os.environ.get("MOD_HTML_DIR", "/app/html")


@router.get("/js/templates.js")
async def bulk_template_loader():
    """
    Load all HTML templates and convert them to JavaScript TEMPLATES object

    This endpoint replicates the original BulkTemplateLoader functionality,
    loading all .html files from the include directory and converting them
    to a JavaScript object for client-side templating.
    """
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


@router.get("/js/{filename}")
async def serve_js_files(filename: str):
    """
    Serve static JS files (templates.js is handled by the endpoint above)

    Custom handler for JavaScript files with security checks to prevent
    directory traversal attacks.
    """
    js_dir = os.path.join(HTML_DIR, "js")
    file_path = os.path.join(js_dir, filename)

    # Security check to prevent directory traversal
    if not os.path.commonpath([js_dir, file_path]) == js_dir:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/javascript")


# Static file mount configurations
def get_static_mounts():
    """
    Return static file mount configurations for the main application

    Returns a list of tuples (path, directory, name) for static file mounts.
    This is used by the main application to set up StaticFiles mounts.
    """
    return [
        ("/css", os.path.join(HTML_DIR, "css"), "css"),
        ("/js/lib", os.path.join(HTML_DIR, "js", "lib"), "js_lib"),
        ("/js/utils", os.path.join(HTML_DIR, "js", "utils"), "js_utils"),
        ("/img", os.path.join(HTML_DIR, "img"), "img"),
        ("/fonts", os.path.join(HTML_DIR, "fonts"), "fonts"),
        ("/resources", os.path.join(HTML_DIR, "resources"), "resources"),
        ("/static", HTML_DIR, "static"),  # Fallback static mount
    ]
