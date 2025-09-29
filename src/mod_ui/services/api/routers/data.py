"""
Data Management Router

Handles configuration, favorites, snapshots, and other data management endpoints.
"""

import json
import logging
import os
import tempfile

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["data"])

# File paths
FAVORITES_JSON_FILE = os.environ.get("MOD_FAVORITES_FILE", "/app/data/favorites.json")
PREFERENCES_JSON_FILE = os.environ.get(
    "MOD_PREFERENCES_FILE", "/app/data/preferences.json"
)
BANKS_JSON_FILE = os.environ.get("MOD_BANKS_FILE", "/app/data/banks.json")


def safe_json_load(filepath: str, default_value):
    """Safely load JSON file with fallback to default value"""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {filepath}: {e}")

    # If default_value is a type (like dict, list), instantiate it
    if isinstance(default_value, type):
        return default_value()
    return default_value


def save_json_atomically(filepath: str, data):
    """Save JSON data atomically using temporary file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Write to temporary file first
    temp_path = filepath + ".tmp"
    with open(temp_path, "w") as f:
        json.dump(data, f, indent=2)

    # Atomic rename
    os.rename(temp_path, filepath)


@router.get("/snapshot/name")
async def get_snapshot_name(id: int = 0):
    """
    Get snapshot name by ID - used during loading sequence

    Returns the name of a snapshot for the given ID.
    Used by the frontend during pedalboard loading.
    """
    try:
        # For now, return default names based on ID
        # TODO: Load from actual snapshot data
        if id == 0:
            return {"ok": True, "name": "Default"}
        else:
            return {"ok": True, "name": f"Snapshot {id}"}
    except Exception as e:
        logger.error(f"Error getting snapshot name for ID {id}: {e}")
        return {"ok": False, "name": "Unknown"}


@router.get("/favorites")
async def get_favorites():
    """
    Get user favorites list

    Returns the list of plugin URIs that the user has marked as favorites.
    """
    favorites = safe_json_load(FAVORITES_JSON_FILE, list)
    return JSONResponse(favorites)


@router.post("/favorites/add")
async def add_favorite(uri: str = Form(...)):
    """
    Add plugin to favorites

    Adds a plugin URI to the user's favorites list and saves it to disk.
    """
    try:
        favorites = safe_json_load(FAVORITES_JSON_FILE, list)

        if uri not in favorites:
            favorites.append(uri)
            save_json_atomically(FAVORITES_JSON_FILE, favorites)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error adding favorite {uri}: {e}")
        return JSONResponse(False)


@router.post("/favorites/remove")
async def remove_favorite(uri: str = Form(...)):
    """
    Remove plugin from favorites

    Removes a plugin URI from the user's favorites list and saves the changes.
    """
    try:
        favorites = safe_json_load(FAVORITES_JSON_FILE, list)

        if uri in favorites:
            favorites.remove(uri)
            save_json_atomically(FAVORITES_JSON_FILE, favorites)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error removing favorite {uri}: {e}")
        return JSONResponse(False)


@router.post("/config/set")
async def save_config_value(key: str = Form(...), value: str = Form(...)):
    """
    Set a single configuration value

    Saves a configuration key-value pair to the preferences file.
    Matches the original SaveSingleConfigValue functionality.
    """
    try:
        # Load existing preferences
        preferences = safe_json_load(PREFERENCES_JSON_FILE, dict)

        # Update the value
        preferences[key] = value

        # Save preferences atomically
        save_json_atomically(PREFERENCES_JSON_FILE, preferences)

        return JSONResponse(True)
    except Exception as e:
        logger.error(f"Error saving config value {key}={value}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/banks")
async def get_banks():
    """
    List all available banks

    Returns the list of preset banks available in the system.
    """
    banks = safe_json_load(BANKS_JSON_FILE, list)

    # Default banks if file doesn't exist
    if not banks:
        banks = [{"id": 0, "name": "Default Bank", "pedalboards": []}]

    return JSONResponse({"success": True, "data": {"banks": banks}})


@router.post("/bank/new")
async def create_bank(name: str = Form(...)):
    """
    Create a new bank

    Creates a new preset bank with the given name and returns the bank data.
    """
    try:
        banks = safe_json_load(BANKS_JSON_FILE, list)

        # Generate new bank ID
        bank_id = max([bank.get("id", 0) for bank in banks], default=0) + 1

        new_bank = {"id": bank_id, "name": name, "pedalboards": []}
        banks.append(new_bank)

        # Save banks
        save_json_atomically(BANKS_JSON_FILE, banks)

        return JSONResponse({"success": True, "data": new_bank})
    except Exception as e:
        logger.error(f"Error creating bank: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pedalboards/list")
async def list_pedalboards():
    """
    List available pedalboards

    Returns the list of pedalboards available in the system.
    """
    try:
        pedalboards_dir = os.environ.get("MOD_PEDALBOARDS_DIR", "/app/data/pedalboards")
        pedalboards = []

        if os.path.exists(pedalboards_dir):
            for item in os.listdir(pedalboards_dir):
                item_path = os.path.join(pedalboards_dir, item)
                if os.path.isdir(item_path):
                    # Look for manifest.ttl or pedalboard.json
                    manifest_path = os.path.join(item_path, "manifest.ttl")
                    json_path = os.path.join(item_path, "pedalboard.json")

                    if os.path.exists(manifest_path) or os.path.exists(json_path):
                        pedalboards.append(
                            {
                                "bundle": item,
                                "name": item.replace("_", " ").title(),
                                "path": item_path,
                            }
                        )

        return JSONResponse({"success": True, "data": {"pedalboards": pedalboards}})
    except Exception as e:
        logger.error(f"Error listing pedalboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))
