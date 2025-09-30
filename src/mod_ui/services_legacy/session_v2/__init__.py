"""
Modern Session Service for MOD UI

This is a complete rewrite of the session management functionality using
FastAPI, AsyncIO, and modern Python patterns. It replaces the legacy
Tornado-based session system with a microservice architecture.

Architecture:
- State Manager Service: Pedalboard and session state management
- WebSocket Hub Service: Real-time communication with clients
- Event Bus System: Service coordination and communication
- API Gateway: REST endpoints and WebSocket management

Author: MOD UI Team
Version: 2.0.0 (Complete Rewrite)
"""

__version__ = "2.0.0"
__author__ = "MOD UI Team"
