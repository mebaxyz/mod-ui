"""
Event Types for WebSocket Gateway

Centralized definition of all event types that can be routed through the gateway.
"""

from enum import Enum
from typing import List


class EventType(str, Enum):
    """All event types supported by the WebSocket Gateway"""

    # Session events
    SESSION_STARTED = "session_started"
    SESSION_STOPPED = "session_stopped"
    SESSION_RESET = "session_reset"
    SESSION_ERROR = "session_error"
    SESSION_TRANSPORT_CHANGED = "session_transport_changed"
    SESSION_CONFIG_CHANGED = "session_config_changed"
    SESSION_STATS_UPDATED = "session_stats_updated"

    # Pedalboard events
    PEDALBOARD_LOADED = "pedalboard_loaded"
    PEDALBOARD_SAVED = "pedalboard_saved"
    PEDALBOARD_CHANGED = "pedalboard_changed"
    PEDALBOARD_CLEARED = "pedalboard_cleared"
    PEDALBOARD_SIZE_CHANGED = "pedalboard_size_changed"

    # Plugin events
    PLUGIN_ADDED = "plugin_added"
    PLUGIN_REMOVED = "plugin_removed"
    PLUGIN_MOVED = "plugin_moved"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    PLUGIN_PRESET_CHANGED = "plugin_preset_changed"
    PLUGIN_PARAMETER_CHANGED = "plugin_parameter_changed"

    # Parameter events
    PARAMETER_CHANGED = "parameter_changed"
    PARAMETER_ADDRESSED = "parameter_addressed"
    PARAMETER_UNADDRESSED = "parameter_unaddressed"

    # Connection events
    CONNECTION_ADDED = "connection_added"
    CONNECTION_REMOVED = "connection_removed"
    AUDIO_CONNECTION_ADDED = "audio_connection_added"
    AUDIO_CONNECTION_REMOVED = "audio_connection_removed"

    # Hardware events
    HARDWARE_CONNECTED = "hardware_connected"
    HARDWARE_DISCONNECTED = "hardware_disconnected"
    HARDWARE_STATUS_UPDATED = "hardware_status_updated"
    HARDWARE_ERROR = "hardware_error"
    HARDWARE_DEVICE_ADDED = "hardware_device_added"
    HARDWARE_DEVICE_REMOVED = "hardware_device_removed"

    # Control Chain events
    CONTROL_CHAIN_DEVICE_ADDED = "control_chain_device_added"
    CONTROL_CHAIN_DEVICE_REMOVED = "control_chain_device_removed"
    CONTROL_CHAIN_DEVICE_CONNECTED = "control_chain_device_connected"
    CONTROL_CHAIN_DEVICE_DISCONNECTED = "control_chain_device_disconnected"
    CONTROL_CHAIN_ACTUATOR_ADDED = "control_chain_actuator_added"

    # HMI events
    HMI_MESSAGE_RECEIVED = "hmi_message_received"
    HMI_CONTROL_ADDED = "hmi_control_added"
    HMI_CONTROL_CHANGED = "hmi_control_changed"
    HMI_CONTROL_REMOVED = "hmi_control_removed"
    HMI_PING_RESPONSE = "hmi_ping_response"

    # Audio engine events
    AUDIO_ENGINE_STARTED = "audio_engine_started"
    AUDIO_ENGINE_STOPPED = "audio_engine_stopped"
    AUDIO_ENGINE_XRUN = "audio_engine_xrun"
    AUDIO_ENGINE_BUFFER_SIZE_CHANGED = "audio_engine_buffer_size_changed"
    AUDIO_ENGINE_SAMPLE_RATE_CHANGED = "audio_engine_sample_rate_changed"

    # System events
    SYSTEM_STATS_UPDATED = "system_stats_updated"
    SYSTEM_CPU_LOAD_CHANGED = "system_cpu_load_changed"
    SYSTEM_MEMORY_CHANGED = "system_memory_changed"
    SYSTEM_TEMPERATURE_CHANGED = "system_temperature_changed"

    # Client events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    CLIENT_SUBSCRIBED = "client_subscribed"
    CLIENT_UNSUBSCRIBED = "client_unsubscribed"

    # Recording events
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    RECORDING_PAUSED = "recording_paused"
    RECORDING_ERROR = "recording_error"

    # Screenshot events
    SCREENSHOT_GENERATED = "screenshot_generated"
    SCREENSHOT_ERROR = "screenshot_error"

    # Service events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    SERVICE_HEALTH_CHANGED = "service_health_changed"
    SERVICE_ERROR = "service_error"

    # Gateway events
    GATEWAY_CLIENT_WELCOME = "gateway_client_welcome"
    GATEWAY_BROADCAST = "gateway_broadcast"
    GATEWAY_SUBSCRIPTION_CONFIRMED = "gateway_subscription_confirmed"
    GATEWAY_ERROR = "gateway_error"

    # Special events
    ALL_EVENTS = "*"  # Subscribe to all events
    PING = "ping"
    PONG = "pong"


class EventPriority(str, Enum):
    """Event priority levels for routing"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(str, Enum):
    """WebSocket message types"""

    # Client -> Gateway
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    REQUEST_STATUS = "request_status"

    # Gateway -> Client
    WELCOME = "welcome"
    EVENT = "event"
    PONG = "pong"
    STATUS = "status"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    UNSUBSCRIPTION_CONFIRMED = "unsubscription_confirmed"
    ERROR = "error"

    # Legacy compatibility
    DATA_READY = "data_ready"
    LOADING_START = "loading_start"
    LOADING_END = "loading_end"
    TRANSPORT = "transport"
    TRUEBYPASS = "truebypass"
    SIZE = "size"
    STATS = "stats"
    SYS_STATS = "sys_stats"


# Event type groupings for easier subscription management
EVENT_GROUPS = {
    "session": [
        EventType.SESSION_STARTED,
        EventType.SESSION_STOPPED,
        EventType.SESSION_RESET,
        EventType.SESSION_TRANSPORT_CHANGED,
        EventType.SESSION_CONFIG_CHANGED,
        EventType.SESSION_STATS_UPDATED,
    ],
    "pedalboard": [
        EventType.PEDALBOARD_LOADED,
        EventType.PEDALBOARD_SAVED,
        EventType.PEDALBOARD_CHANGED,
        EventType.PEDALBOARD_CLEARED,
        EventType.PEDALBOARD_SIZE_CHANGED,
    ],
    "plugins": [
        EventType.PLUGIN_ADDED,
        EventType.PLUGIN_REMOVED,
        EventType.PLUGIN_MOVED,
        EventType.PLUGIN_ENABLED,
        EventType.PLUGIN_DISABLED,
        EventType.PLUGIN_PRESET_CHANGED,
        EventType.PLUGIN_PARAMETER_CHANGED,
    ],
    "hardware": [
        EventType.HARDWARE_CONNECTED,
        EventType.HARDWARE_DISCONNECTED,
        EventType.HARDWARE_STATUS_UPDATED,
        EventType.HARDWARE_DEVICE_ADDED,
        EventType.HARDWARE_DEVICE_REMOVED,
    ],
    "system": [
        EventType.SYSTEM_STATS_UPDATED,
        EventType.SYSTEM_CPU_LOAD_CHANGED,
        EventType.SYSTEM_MEMORY_CHANGED,
        EventType.SYSTEM_TEMPERATURE_CHANGED,
    ],
    "audio": [
        EventType.AUDIO_ENGINE_STARTED,
        EventType.AUDIO_ENGINE_STOPPED,
        EventType.AUDIO_ENGINE_XRUN,
        EventType.AUDIO_CONNECTION_ADDED,
        EventType.AUDIO_CONNECTION_REMOVED,
    ],
}


def get_events_for_group(group_name: str) -> List[EventType]:
    """Get all event types for a specific group"""
    return EVENT_GROUPS.get(group_name, [])


def get_all_event_types() -> List[EventType]:
    """Get all available event types"""
    return [
        event_type for event_type in EventType if event_type != EventType.ALL_EVENTS
    ]
