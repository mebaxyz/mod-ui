"""
Effects Service Handlers
Handles all effects-related operations via Redis pub/sub
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from servicebus import ServiceClient, ServiceServer
from servicebus.models import ServiceEvent, ServiceRequest

from .models import *

logger = logging.getLogger(__name__)


class EffectsServiceHandlers:
    """Handlers for the Effects Service"""

    def __init__(self, service_instance=None):
        self.logger = logger
        # Initialize service client for communicating with other services
        self.service_client = ServiceClient("effects_service")
        # Store service instance for event publishing
        self.service = service_instance
        # Placeholder for plugin data - in production this would load from LV2/real plugin system
        self._mock_plugins = [
            {
                "uri": "http://lv2plug.in/plugins/eg-amp",
                "name": "Simple Amplifier",
                "brand": "LV2",
                "label": "Simple Amp",
                "category": ["Utility"],
                "ports": {
                    "control": {
                        "input": [
                            {
                                "name": "Gain",
                                "symbol": "gain",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "default": 0.5,
                            }
                        ]
                    },
                    "audio": {
                        "input": [{"name": "Input", "symbol": "input"}],
                        "output": [{"name": "Output", "symbol": "output"}],
                    },
                },
            },
            {
                "uri": "http://lv2plug.in/plugins/eg-reverb",
                "name": "Simple Reverb",
                "brand": "LV2",
                "label": "Simple Reverb",
                "category": ["Reverb"],
                "ports": {
                    "control": {
                        "input": [
                            {
                                "name": "Room Size",
                                "symbol": "room_size",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "default": 0.3,
                            }
                        ]
                    },
                    "audio": {
                        "input": [{"name": "Input", "symbol": "input"}],
                        "output": [{"name": "Output", "symbol": "output"}],
                    },
                },
            },
        ]

    async def handle_effect_add(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect add request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectAddRequest(**data)

            instance = data.get("instance", "")
            if not instance:
                return EffectAddResponse(
                    success=False, error="Instance required"
                ).dict()

            # Find plugin in mock data
            plugin_data = None
            for plugin in self._mock_plugins:
                if plugin["uri"] == req.uri:
                    plugin_data = plugin
                    break

            if not plugin_data:
                return EffectAddResponse(
                    success=False, error=f"Plugin not found: {req.uri}"
                ).dict()

            # Call audio engine to actually add the plugin to the audio graph
            try:
                audio_response = await self.service_client.call(
                    target_service="audio-engine",
                    request_type="add_plugin",
                    data={
                        "instance_id": instance,
                        "plugin_uri": req.uri,
                        "x": req.x,
                        "y": req.y,
                    },
                )

                if not audio_response or not audio_response.get("success"):
                    error_msg = (
                        audio_response.get("error", "Audio engine add failed")
                        if audio_response
                        else "Audio engine not available"
                    )
                    self.logger.warning(f"Audio engine add failed: {error_msg}")
                    # Continue anyway for development - return plugin data even if audio engine fails

            except Exception as audio_error:
                self.logger.warning(f"Audio engine communication failed: {audio_error}")
                # Continue anyway for development

            # Notify webui-gateway via ServiceBus to broadcast WebSocket message
            try:
                await self._notify_plugin_added(instance, req.uri, req.x, req.y)
            except Exception as notify_error:
                self.logger.warning(
                    f"Failed to notify webui-gateway of plugin add: {notify_error}"
                )

            return EffectAddResponse(
                success=True, instance=instance, plugin_data=plugin_data
            ).dict()

        except Exception as e:
            self.logger.error(f"Effect add error: {e}")
            return EffectAddResponse(success=False, error=str(e)).dict()

    async def handle_effect_remove(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect remove request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectRemoveRequest(**data)

            # In production, this would remove from the actual audio graph
            # Notify webui-gateway via ServiceBus to broadcast WebSocket message
            try:
                await self._notify_plugin_removed(req.instance)
            except Exception as notify_error:
                self.logger.warning(
                    f"Failed to notify webui-gateway of plugin remove: {notify_error}"
                )

            return EffectRemoveResponse(success=True).dict()

        except Exception as e:
            self.logger.error(f"Effect remove error: {e}")
            return EffectRemoveResponse(success=False, error=str(e)).dict()

    async def handle_effect_get(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect get request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectGetRequest(**data)

            # Find plugin in mock data
            plugin_data = None
            for plugin in self._mock_plugins:
                if plugin["uri"] == req.uri:
                    plugin_data = plugin
                    break

            if not plugin_data:
                return EffectGetResponse(
                    success=False, error=f"Plugin not found: {req.uri}"
                ).dict()

            return EffectGetResponse(success=True, plugin_data=plugin_data).dict()

        except Exception as e:
            self.logger.error(f"Effect get error: {e}")
            return EffectGetResponse(success=False, error=str(e)).dict()

    async def handle_effect_list(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect list request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectListRequest(**data)

            return EffectListResponse(success=True, plugins=self._mock_plugins).dict()

        except Exception as e:
            self.logger.error(f"Effect list error: {e}")
            return EffectListResponse(success=False, error=str(e)).dict()

    async def handle_effect_connect(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect connect request"""
        try:
            req = EffectConnectRequest(**request.data)

            # In production, this would create audio connections
            return EffectConnectResponse(success=True).dict()

        except Exception as e:
            self.logger.error(f"Effect connect error: {e}")
            return EffectConnectResponse(success=False, error=str(e)).dict()

    async def handle_effect_disconnect(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect disconnect request"""
        try:
            req = EffectDisconnectRequest(**request.data)

            # In production, this would remove audio connections
            return EffectDisconnectResponse(success=True).dict()

        except Exception as e:
            self.logger.error(f"Effect disconnect error: {e}")
            return EffectDisconnectResponse(success=False, error=str(e)).dict()

    async def handle_effect_parameter_set(
        self, request: ServiceRequest
    ) -> Dict[str, Any]:
        """Handle effect parameter set request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectParameterSetRequest(**data)

            # In production, this would set parameter values in audio engine
            try:
                audio_response = await self.service_client.call(
                    target_service="audio-engine",
                    request_type="set_parameter",
                    data={
                        "instance": req.instance,
                        "symbol": req.symbol,
                        "value": req.value,
                    },
                )

                if not audio_response or not audio_response.get("success"):
                    error_msg = (
                        audio_response.get("error", "Audio engine parameter set failed")
                        if audio_response
                        else "Audio engine not available"
                    )
                    self.logger.warning(
                        f"Audio engine parameter set failed: {error_msg}"
                    )
                    # Continue anyway for development

            except Exception as audio_error:
                self.logger.warning(f"Audio engine communication failed: {audio_error}")
                # Continue anyway for development

            # Notify webui-gateway via ServiceBus to broadcast WebSocket message
            try:
                await self._notify_parameter_changed(
                    req.instance, req.symbol, req.value
                )
            except Exception as notify_error:
                self.logger.warning(
                    f"Failed to notify webui-gateway of parameter change: {notify_error}"
                )

            return EffectParameterSetResponse(success=True).dict()

        except Exception as e:
            self.logger.error(f"Effect parameter set error: {e}")
            return EffectParameterSetResponse(success=False, error=str(e)).dict()

    async def handle_effect_parameter_address(
        self, request: ServiceRequest
    ) -> Dict[str, Any]:
        """Handle effect parameter address request"""
        try:
            req = EffectParameterAddressRequest(**request.data)

            # In production, this would set up parameter addressing
            return EffectParameterAddressResponse(
                success=True, addressing_data=req.addressing_data
            ).dict()

        except Exception as e:
            self.logger.error(f"Effect parameter address error: {e}")
            return EffectParameterAddressResponse(success=False, error=str(e)).dict()

    async def handle_effect_preset_load(
        self, request: ServiceRequest
    ) -> Dict[str, Any]:
        """Handle effect preset load request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectPresetLoadRequest(**data)

            # In production, this would load presets
            result = EffectPresetLoadResponse(success=True).dict()

            # Broadcast preset change via WebSocket
            if result.get("success"):
                await self._notify_preset_change(req.instance, req.preset_uri)

            return result

        except Exception as e:
            self.logger.error(f"Effect preset load error: {e}")
            return EffectPresetLoadResponse(success=False, error=str(e)).dict()

    async def handle_effect_preset_save(
        self, request: ServiceRequest
    ) -> Dict[str, Any]:
        """Handle effect preset save request"""
        try:
            # Handle both HTTP requests via webui-gateway and direct ServiceBus calls
            if hasattr(request, "data"):
                data = request.data
            else:
                data = request

            req = EffectPresetSaveRequest(**data)

            # In production, this would save presets
            result = EffectPresetSaveResponse(
                success=True, bundle_path="placeholder_path"
            ).dict()

            # Broadcast preset save notification via WebSocket
            if result.get("success"):
                await self._notify_preset_saved(
                    req.instance, req.name, result.get("bundle_path", "")
                )

            return result

        except Exception as e:
            self.logger.error(f"Effect preset save error: {e}")
            return EffectPresetSaveResponse(success=False, error=str(e)).dict()

    async def handle_effect_preset_delete(
        self, request: ServiceRequest
    ) -> Dict[str, Any]:
        """Handle effect preset delete request"""
        try:
            req = EffectPresetDeleteRequest(**request.data)

            # In production, this would delete presets
            return EffectPresetDeleteResponse(success=True).dict()

        except Exception as e:
            self.logger.error(f"Effect preset delete error: {e}")
            return EffectPresetDeleteResponse(success=False, error=str(e)).dict()

    async def handle_effect_image(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect image request"""
        try:
            req = EffectImageRequest(**request.data)

            # In production, this would return actual plugin images
            # For now, return a placeholder
            return EffectImageResponse(
                success=False, error="Image not implemented yet"
            ).dict()

        except Exception as e:
            self.logger.error(f"Effect image error: {e}")
            return EffectImageResponse(success=False, error=str(e)).dict()

    async def handle_effect_file(self, request: ServiceRequest) -> Dict[str, Any]:
        """Handle effect file request"""
        try:
            req = EffectFileRequest(**request.data)

            # In production, this would return actual plugin files
            return EffectFileResponse(
                success=False, error="File serving not implemented yet"
            ).dict()

        except Exception as e:
            self.logger.error(f"Effect file error: {e}")
            return EffectFileResponse(success=False, error=str(e)).dict()

    async def _notify_plugin_added(self, instance: str, uri: str, x: float, y: float):
        """Notify webui-gateway to broadcast plugin add WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format expected by frontend: "add {instance} {uri} {x} {y} {bypassed} {pVersion} {offBuild}"
            websocket_message = f"add {instance} {uri} {x} {y} 0 1.0 0"  # bypassed=0, pVersion=1.0, offBuild=0

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "plugin_add",
                    "instance": instance,
                    "uri": uri,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published plugin add event for: {instance}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing plugin add event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_plugin_removed(self, instance: str):
        """Notify webui-gateway to broadcast plugin remove WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format expected by frontend: "remove {instance}"
            websocket_message = f"remove {instance}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "plugin_remove",
                    "instance": instance,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published plugin remove event for: {instance}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing plugin remove event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_parameter_changed(self, instance: str, symbol: str, value: float):
        """Notify webui-gateway to broadcast parameter change WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format expected by frontend: "param_set {instance} {symbol} {value}"
            websocket_message = f"param_set {instance} {symbol} {value}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "parameter_change",
                    "instance": instance,
                    "symbol": symbol,
                    "value": value,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published parameter change event: {instance}/{symbol}={value}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing parameter change event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_preset_change(self, instance: str, preset_uri: str):
        """Notify webui-gateway to broadcast preset change WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format expected by frontend: "preset {instance} {value}"
            # preset_uri is the "value" - if null/None, send empty string
            preset_value = preset_uri if preset_uri else ""
            websocket_message = f"preset {instance} {preset_value}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "preset_change",
                    "instance": instance,
                    "preset_uri": preset_value,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published preset change event: {instance}={preset_value}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing preset change event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_preset_saved(self, instance: str, name: str, bundle_path: str):
        """Notify webui-gateway to broadcast preset saved WebSocket message via ServiceBus events"""
        try:
            # Custom message format for preset save notification
            websocket_message = f"preset_saved {instance} {name} {bundle_path}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "preset_save",
                    "instance": instance,
                    "name": name,
                    "bundle_path": bundle_path,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published preset saved event: {instance}/{name}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing preset saved event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_hardware_map(
        self,
        instance: str,
        symbol: str,
        actuator: str,
        min_val: float,
        max_val: float,
        def_val: float,
        steps: int,
        label: str,
        tempo: bool,
        dividers: str,
        page: int,
        subpage: int,
        group: str,
        feedback: bool,
        bypass: bool,
    ):
        """Notify webui-gateway to broadcast hardware map WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format: "hw_map {instance} {symbol} {actuator} {min} {max} {def} {steps} {label} {tempo} {dividers} {page} {subpage} {group} {feedback} {bypass}"
            tempo_val = "1" if tempo else "0"
            feedback_val = "1" if feedback else "0"
            bypass_val = "1" if bypass else "0"

            websocket_message = f"hw_map {instance} {symbol} {actuator} {min_val} {max_val} {def_val} {steps} {label} {tempo_val} {dividers} {page} {subpage} {group} {feedback_val} {bypass_val}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "hardware_map",
                    "instance": instance,
                    "symbol": symbol,
                    "actuator": actuator,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published hardware map event: {instance}/{symbol}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing hardware map event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_hardware_add(self, instance: str, uri: str, label: str):
        """Notify webui-gateway to broadcast hardware add WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format: "hw_add {instance} {uri} {label}"
            websocket_message = f"hw_add {instance} {uri} {label}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "hardware_add",
                    "instance": instance,
                    "uri": uri,
                    "label": label,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published hardware add event: {instance}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing hardware add event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation

    async def _notify_hardware_remove(self, instance: str):
        """Notify webui-gateway to broadcast hardware remove WebSocket message via ServiceBus events"""
        try:
            # WebSocket message format: "hw_rem {instance}"
            websocket_message = f"hw_rem {instance}"

            # Publish WebSocket broadcast event via ServiceBus
            if self.service:
                event_data = {
                    "type": "legacy_websocket",
                    "content": websocket_message,
                    "message_type": "hardware_remove",
                    "instance": instance,
                }

                await self.service.publish_event("websocket_broadcast", event_data)
                self.logger.info(
                    f"Successfully published hardware remove event: {instance}"
                )
            else:
                self.logger.warning(
                    "Service instance not available for event publishing"
                )

        except Exception as e:
            self.logger.error(f"Error publishing hardware remove event: {e}")
            # Don't re-raise - WebSocket notification failure shouldn't break the main operation
