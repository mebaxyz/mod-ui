"""
Favorites API Router

Handles user favorites management for the WebSocket Gateway.
"""

import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])

# Mock favorites storage - in production this would use a proper database
FAVORITES_FILE = "/tmp/mod_ui_favorites.json"
_favorites_cache = None


def _load_favorites() -> list:
    """Load favorites from storage"""
    global _favorites_cache
    if _favorites_cache is not None:
        return _favorites_cache

    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, "r") as f:
                _favorites_cache = json.load(f)
        else:
            _favorites_cache = []
    except Exception as e:
        logger.error(f"Failed to load favorites: {e}")
        _favorites_cache = []

    return _favorites_cache


def _save_favorites(favorites: list):
    """Save favorites to storage"""
    global _favorites_cache
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(favorites, f)
        _favorites_cache = favorites
    except Exception as e:
        logger.error(f"Failed to save favorites: {e}")
        raise


@router.post("/add")
async def add_favorite(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a plugin to the user's favorites"""
    try:
        uri = data.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="URI is required")

        favorites = _load_favorites()
        if uri not in favorites:
            favorites.append(uri)
            _save_favorites(favorites)

        return {"ok": True, "uri": uri}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add favorite {uri}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add favorite")


@router.post("/remove")
async def remove_favorite(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a plugin from the user's favorites"""
    try:
        uri = data.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="URI is required")

        favorites = _load_favorites()
        if uri in favorites:
            favorites.remove(uri)
            _save_favorites(favorites)

        return {"ok": True, "uri": uri}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite {uri}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove favorite")


@router.get("/list")
async def list_favorites() -> Dict[str, Any]:
    """Get the list of user favorites"""
    try:
        favorites = _load_favorites()
        return {"favorites": favorites}
    except Exception as e:
        logger.error(f"Failed to list favorites: {e}")
        raise HTTPException(status_code=500, detail="Failed to list favorites")
