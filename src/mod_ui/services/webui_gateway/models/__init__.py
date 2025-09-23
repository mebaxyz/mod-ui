"""
Models for WebSocket Gateway Service

Data models and schemas for the WebSocket Gateway service.
"""

# Import all models from the main models file
import importlib.util
import os
import sys

# Load the models.py file directly
models_path = os.path.join(os.path.dirname(__file__), "..", "models.py")
spec = importlib.util.spec_from_file_location("models", models_path)
models_module = importlib.util.module_from_spec(spec)
sys.modules["models"] = models_module
spec.loader.exec_module(models_module)

ClientConnection = models_module.ClientConnection
ConnectionStatus = models_module.ConnectionStatus
EventRouterStats = models_module.EventRouterStats
EventSubscription = models_module.EventSubscription
GatewayMessage = models_module.GatewayMessage
GatewayStats = models_module.GatewayStats
ServiceStatus = models_module.ServiceStatus

__all__ = [
    # Original models
    "ClientConnection",
    "ConnectionStatus",
    "EventSubscription",
    "GatewayMessage",
    "GatewayStats",
    "ServiceStatus",
    "EventRouterStats",
]
