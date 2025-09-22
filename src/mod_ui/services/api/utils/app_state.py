"""
Application State Management

Global application state for the MOD UI API service.
"""

from typing import List

from fastapi import WebSocket


class AppState:
    """Global application state"""

    def __init__(self):
        self.favorites: List[str] = []
        self.websocket_clients: List[WebSocket] = []


# Global app state instance
app_state = AppState()
