"""
Direct ZeroMQ Client

Minimal ZeroMQ client for calling remote services without ServiceBus package.
"""

import asyncio
import json
import logging
import uuid
import zlib
from datetime import datetime
from typing import Any, Dict, Optional

import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class ZMQClient:
    """
    Direct ZeroMQ client for RPC communication
    """

    def __init__(self, client_name: str, base_port: int = 5555):
        self.client_name = client_name
        self.base_port = base_port
        self.context = zmq.asyncio.Context()
        
        # REQ sockets for calling other services
        self.req_sockets = {}
        
        # State
        self._running = False

    def _get_service_rpc_port(self, service_name: str) -> int:
        """Get the RPC port for a service"""
        service_hash = zlib.crc32(service_name.encode("utf-8")) % 1000
        return self.base_port + service_hash

    async def start(self) -> bool:
        """Start the ZeroMQ client"""
        try:
            self._running = True
            logger.info("ZMQ Client '%s' started successfully", self.client_name)
            return True
            
        except Exception as e:
            logger.error("Failed to start ZMQ client '%s': %s", self.client_name, e)
            return False

    async def stop(self):
        """Stop the ZeroMQ client"""
        self._running = False
        
        # Close sockets
        for socket in self.req_sockets.values():
            socket.close()
        self.req_sockets.clear()
        
        # Terminate context
        self.context.term()
        
        logger.info("ZMQ Client '%s' stopped", self.client_name)

    async def call(self, service_name: str, method: str, timeout: Optional[float] = 5.0, **kwargs) -> Any:
        """Call a method on another service"""
        try:
            # Get or create REQ socket for this service
            if service_name not in self.req_sockets:
                service_port = self._get_service_rpc_port(service_name)
                req_socket = self.context.socket(zmq.REQ)
                req_socket.connect(f"tcp://127.0.0.1:{service_port}")
                self.req_sockets[service_name] = req_socket
            
            req_socket = self.req_sockets[service_name]
            
            # Create request
            request_data = {
                "method": method,
                "params": kwargs,
                "source_service": self.client_name,
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
            }
            
            # Send request and wait for response
            await req_socket.send_json(request_data)
            
            if timeout is not None:
                response_data = await asyncio.wait_for(req_socket.recv_json(), timeout=timeout)
            else:
                response_data = await req_socket.recv_json()
            
            if response_data.get("error"):
                raise RuntimeError(f"Remote service error: {response_data['error']}")
            
            return response_data.get("result")
            
        except Exception as e:
            logger.error("Failed to call %s.%s: %s", service_name, method, e)
            raise

    def is_connected(self) -> bool:
        """Check if the client is connected (always True for direct ZMQ)"""
        return self._running
        
    async def request(self, service: str, method: str, timeout: Optional[float] = 5.0, **params) -> Dict[str, Any]:
        """Request method compatible with ResilientServiceBus interface"""
        try:
            result = await self.call(service, method, timeout=timeout, **params)
            # Wrap result in the format expected by client interface
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            logger.error("Request failed: %s", e)
            # Return error in expected format
            return {"success": False, "error": str(e)}