"""
MOD UI - Hardware Interface Service

Consolidated service handling physical controls, MIDI I/O, display management, and hardware communication.
This service consolidates hardware_service and provides comprehensive hardware abstraction.
"""

import asyncio
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ...common.models import ServiceHealth, ServiceStatus
from ...common.resilient_service_bus import ResilientServiceBus

# Configuration
SERVICE_NAME = "hardware_interface"
SERVICE_PORT = int(os.getenv("HARDWARE_INTERFACE_PORT", "8083"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Hardware configuration
MIDI_BUFFER_SIZE = 1024
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
ENCODER_RESOLUTION = 24
BUTTON_DEBOUNCE_MS = 50

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Enums and Data Models
class ControlType(Enum):
    ENCODER = "encoder"
    BUTTON = "button"
    FOOTSWITCH = "footswitch"
    EXPRESSION_PEDAL = "expression_pedal"
    POTENTIOMETER = "potentiometer"


class HardwareEvent(Enum):
    BUTTON_PRESS = "button_press"
    BUTTON_RELEASE = "button_release"
    ENCODER_TURN = "encoder_turn"
    FOOTSWITCH_PRESS = "footswitch_press"
    FOOTSWITCH_RELEASE = "footswitch_release"
    EXPRESSION_CHANGE = "expression_change"
    MIDI_NOTE_ON = "midi_note_on"
    MIDI_NOTE_OFF = "midi_note_off"
    MIDI_CC = "midi_cc"
    MIDI_PROGRAM_CHANGE = "midi_program_change"


@dataclass
class HardwareControl:
    id: str
    type: ControlType
    name: str
    position: Dict[str, int]  # x, y coordinates
    value: float = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    assignment: Optional[str] = None  # What parameter this controls
    midi_cc: Optional[int] = None
    enabled: bool = True


@dataclass
class MidiMessage:
    timestamp: float
    message_type: str
    channel: int
    data1: int
    data2: Optional[int] = None
    raw_bytes: Optional[List[int]] = None


@dataclass
class DisplayContent:
    title: str
    lines: List[str]
    icons: List[Dict[str, Any]] = None
    highlight: Optional[int] = None
    timestamp: Optional[float] = None


# Request/Response Models
class ControlAssignment(BaseModel):
    control_id: str
    parameter_path: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class DisplayUpdate(BaseModel):
    title: str
    lines: List[str]
    highlight: Optional[int] = None


class MidiConfig(BaseModel):
    input_device: Optional[str] = None
    output_device: Optional[str] = None
    channel: int = 1
    enable_thru: bool = False


# Global state
hardware_controls: Dict[str, HardwareControl] = {}
midi_input_devices: List[str] = []
midi_output_devices: List[str] = []
current_display: Optional[DisplayContent] = None
control_assignments: Dict[str, str] = {}  # control_id -> parameter_path
midi_config: MidiConfig = MidiConfig()

# Hardware simulation flags (for development)
SIMULATE_HARDWARE = os.getenv("SIMULATE_HARDWARE", "false").lower() == "true"

# Global instances
service_bus: Optional[ResilientServiceBus] = None
hardware_thread: Optional[threading.Thread] = None
hardware_running = False


class HardwareManager:
    """Manages physical hardware interface"""

    def __init__(self):
        self.controls = {}
        self.callbacks = {}
        self.running = False
        self.midi_in = None
        self.midi_out = None
        self.display = None

    def initialize(self):
        """Initialize hardware components"""
        try:
            if SIMULATE_HARDWARE:
                logger.info("Hardware simulation mode enabled")
                self._init_simulated_hardware()
            else:
                self._init_physical_hardware()

            self.running = True
            logger.info("Hardware manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            return False

    def shutdown(self):
        """Shutdown hardware components"""
        self.running = False
        if self.midi_in:
            try:
                self.midi_in.close()
            except:
                pass
        if self.midi_out:
            try:
                self.midi_out.close()
            except:
                pass
        logger.info("Hardware manager shutdown")

    def _init_simulated_hardware(self):
        """Initialize simulated hardware for development"""
        # Create virtual controls
        self.controls = {
            "encoder_1": HardwareControl(
                "encoder_1", ControlType.ENCODER, "Main Encoder", {"x": 64, "y": 32}
            ),
            "button_1": HardwareControl(
                "button_1", ControlType.BUTTON, "Select Button", {"x": 64, "y": 50}
            ),
            "button_2": HardwareControl(
                "button_2", ControlType.BUTTON, "Menu Button", {"x": 32, "y": 50}
            ),
            "button_3": HardwareControl(
                "button_3", ControlType.BUTTON, "Back Button", {"x": 96, "y": 50}
            ),
            "footswitch_1": HardwareControl(
                "footswitch_1",
                ControlType.FOOTSWITCH,
                "Footswitch 1",
                {"x": 20, "y": 80},
            ),
            "footswitch_2": HardwareControl(
                "footswitch_2",
                ControlType.FOOTSWITCH,
                "Footswitch 2",
                {"x": 108, "y": 80},
            ),
            "expression": HardwareControl(
                "expression",
                ControlType.EXPRESSION_PEDAL,
                "Expression Pedal",
                {"x": 64, "y": 100},
            ),
        }

        global hardware_controls
        hardware_controls = self.controls

    def _init_physical_hardware(self):
        """Initialize physical hardware components"""
        try:
            # Initialize MIDI
            self._init_midi()

            # Initialize display
            self._init_display()

            # Initialize controls (GPIO, ADC, etc.)
            self._init_controls()

        except Exception as e:
            logger.error(f"Failed to initialize physical hardware: {e}")
            raise

    def _init_midi(self):
        """Initialize MIDI interfaces"""
        try:
            import rtmidi

            # MIDI Input
            self.midi_in = rtmidi.MidiIn()
            available_ports = self.midi_in.get_ports()

            global midi_input_devices
            midi_input_devices = available_ports

            if available_ports:
                self.midi_in.open_port(0)
                self.midi_in.set_callback(self._midi_callback)
                logger.info(f"MIDI input opened: {available_ports[0]}")

            # MIDI Output
            self.midi_out = rtmidi.MidiOut()
            output_ports = self.midi_out.get_ports()

            global midi_output_devices
            midi_output_devices = output_ports

            if output_ports:
                self.midi_out.open_port(0)
                logger.info(f"MIDI output opened: {output_ports[0]}")

        except ImportError:
            logger.warning("rtmidi not available, MIDI functionality disabled")
        except Exception as e:
            logger.error(f"MIDI initialization failed: {e}")

    def _init_display(self):
        """Initialize display"""
        try:
            if not SIMULATE_HARDWARE:
                # Initialize actual display (SSD1306, etc.)
                # This would be hardware-specific implementation
                pass

            # Set initial display content
            global current_display
            current_display = DisplayContent(
                title="MOD UI",
                lines=["System Ready", "Hardware OK"],
                timestamp=time.time(),
            )

            logger.info("Display initialized")

        except Exception as e:
            logger.error(f"Display initialization failed: {e}")

    def _init_controls(self):
        """Initialize physical controls"""
        if not SIMULATE_HARDWARE:
            try:
                # Initialize GPIO for buttons and encoders
                # Initialize ADC for expression pedals
                # This would be hardware-specific implementation
                pass
            except Exception as e:
                logger.error(f"Controls initialization failed: {e}")

        # Set up control definitions
        if not SIMULATE_HARDWARE:
            # Real hardware control mapping
            controls_config = {
                "encoder_main": HardwareControl(
                    "encoder_main",
                    ControlType.ENCODER,
                    "Main Encoder",
                    {"x": 64, "y": 32},
                ),
                "button_select": HardwareControl(
                    "button_select", ControlType.BUTTON, "Select", {"x": 64, "y": 50}
                ),
                "button_menu": HardwareControl(
                    "button_menu", ControlType.BUTTON, "Menu", {"x": 32, "y": 50}
                ),
                "button_back": HardwareControl(
                    "button_back", ControlType.BUTTON, "Back", {"x": 96, "y": 50}
                ),
                "footswitch_1": HardwareControl(
                    "footswitch_1", ControlType.FOOTSWITCH, "FS1", {"x": 20, "y": 80}
                ),
                "footswitch_2": HardwareControl(
                    "footswitch_2", ControlType.FOOTSWITCH, "FS2", {"x": 108, "y": 80}
                ),
                "expression": HardwareControl(
                    "expression",
                    ControlType.EXPRESSION_PEDAL,
                    "Expression",
                    {"x": 64, "y": 100},
                ),
            }
        else:
            # Use simulated controls
            controls_config = self.controls

        global hardware_controls
        hardware_controls = controls_config

    def _midi_callback(self, message, data=None):
        """Handle incoming MIDI messages"""
        try:
            msg, deltatime = message

            if len(msg) >= 2:
                status = msg[0]
                data1 = msg[1]
                data2 = msg[2] if len(msg) > 2 else None

                # Parse MIDI message
                msg_type = ""
                channel = status & 0x0F

                if (status & 0xF0) == 0x90:  # Note On
                    msg_type = "note_on"
                elif (status & 0xF0) == 0x80:  # Note Off
                    msg_type = "note_off"
                elif (status & 0xF0) == 0xB0:  # Control Change
                    msg_type = "control_change"
                elif (status & 0xF0) == 0xC0:  # Program Change
                    msg_type = "program_change"

                midi_msg = MidiMessage(
                    timestamp=time.time(),
                    message_type=msg_type,
                    channel=channel,
                    data1=data1,
                    data2=data2,
                    raw_bytes=msg,
                )

                # Process MIDI message
                asyncio.create_task(self._process_midi_message(midi_msg))

        except Exception as e:
            logger.error(f"MIDI callback error: {e}")

    async def _process_midi_message(self, msg: MidiMessage):
        """Process incoming MIDI message"""
        if service_bus:
            await service_bus.publish("midi_message", asdict(msg))

        # Handle MIDI-to-parameter mapping
        if msg.message_type == "control_change":
            await self._handle_midi_cc(msg.data1, msg.data2)

    async def _handle_midi_cc(self, cc_number: int, value: int):
        """Handle MIDI CC messages"""
        # Find control assigned to this CC
        for control_id, control in hardware_controls.items():
            if control.midi_cc == cc_number:
                # Normalize value (0-127 to control range)
                normalized = (value / 127.0) * (
                    control.max_value - control.min_value
                ) + control.min_value
                control.value = normalized

                # Send parameter update if assigned
                if control.assignment and service_bus:
                    await service_bus.request(
                        "audio_processing",
                        "update_parameter",
                        {
                            "plugin_instance": control.assignment.split(".")[0],
                            "parameter": control.assignment.split(".")[1],
                            "value": normalized,
                        },
                    )

                break

    def send_midi(self, message: List[int]):
        """Send MIDI message"""
        if self.midi_out:
            try:
                self.midi_out.send_message(message)
            except Exception as e:
                logger.error(f"MIDI send error: {e}")

    def update_display(self, content: DisplayContent):
        """Update display content"""
        global current_display
        current_display = content

        if not SIMULATE_HARDWARE and self.display:
            try:
                # Update physical display
                # This would be hardware-specific implementation
                pass
            except Exception as e:
                logger.error(f"Display update error: {e}")

    def get_control_value(self, control_id: str) -> Optional[float]:
        """Get current control value"""
        if control_id in hardware_controls:
            if SIMULATE_HARDWARE:
                # Return simulated value
                return hardware_controls[control_id].value
            else:
                # Read from physical hardware
                # This would be hardware-specific implementation
                return hardware_controls[control_id].value
        return None

    def register_callback(self, event_type: HardwareEvent, callback: Callable):
        """Register callback for hardware events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    async def simulate_control_change(self, control_id: str, value: float):
        """Simulate control change (for development)"""
        if SIMULATE_HARDWARE and control_id in hardware_controls:
            control = hardware_controls[control_id]
            control.value = max(control.min_value, min(control.max_value, value))

            # Trigger callbacks
            if service_bus:
                await service_bus.publish(
                    "hardware_event",
                    {
                        "type": "control_change",
                        "control_id": control_id,
                        "value": value,
                    },
                )


# Global hardware manager
hardware_manager = HardwareManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global service_bus, hardware_thread, hardware_running

    # Startup
    logger.info(f"Starting {SERVICE_NAME} service on port {SERVICE_PORT}")

    # Initialize service bus
    service_bus = ResilientServiceBus(SERVICE_NAME, REDIS_URL)
    await service_bus.start()

    # Register service endpoints
    await service_bus.register_service(SERVICE_NAME, f"http://localhost:{SERVICE_PORT}")

    # Initialize hardware
    if hardware_manager.initialize():
        # Start hardware monitoring thread
        hardware_running = True
        hardware_thread = threading.Thread(target=hardware_monitor_thread, daemon=True)
        hardware_thread.start()

    # Start background tasks
    asyncio.create_task(hardware_status_monitor())

    logger.info(f"{SERVICE_NAME} service started successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME} service")
    hardware_running = False
    hardware_manager.shutdown()
    if service_bus:
        await service_bus.stop()


# Create FastAPI app
app = FastAPI(
    title="MOD UI - Hardware Interface Service",
    description="Handles physical controls, MIDI I/O, display management, and hardware communication",
    version="1.0.0",
    lifespan=lifespan,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return ServiceHealth(
        service=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        details={
            "hardware_controls": len(hardware_controls),
            "midi_input_devices": len(midi_input_devices),
            "midi_output_devices": len(midi_output_devices),
            "display_active": current_display is not None,
            "simulation_mode": SIMULATE_HARDWARE,
            "service_bus_connected": (
                service_bus.is_connected() if service_bus else False
            ),
        },
    )


# Hardware Control Endpoints
@app.get("/api/hardware/controls")
async def get_hardware_controls():
    """Get all hardware controls"""
    return {"controls": {k: asdict(v) for k, v in hardware_controls.items()}}


@app.get("/api/hardware/controls/{control_id}")
async def get_control(control_id: str):
    """Get specific control information"""
    if control_id not in hardware_controls:
        raise HTTPException(status_code=404, detail="Control not found")

    control = hardware_controls[control_id]
    current_value = hardware_manager.get_control_value(control_id)

    return {"control": asdict(control), "current_value": current_value}


@app.post("/api/hardware/assignments")
async def assign_control(assignment: ControlAssignment):
    """Assign hardware control to parameter"""
    global control_assignments

    try:
        if assignment.control_id not in hardware_controls:
            raise HTTPException(status_code=404, detail="Control not found")

        # Update control assignment
        control = hardware_controls[assignment.control_id]
        control.assignment = assignment.parameter_path

        if assignment.min_value is not None:
            control.min_value = assignment.min_value
        if assignment.max_value is not None:
            control.max_value = assignment.max_value

        control_assignments[assignment.control_id] = assignment.parameter_path

        return {"message": "Control assigned successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning control: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign control")


@app.delete("/api/hardware/assignments/{control_id}")
async def unassign_control(control_id: str):
    """Remove control assignment"""
    global control_assignments

    try:
        if control_id not in hardware_controls:
            raise HTTPException(status_code=404, detail="Control not found")

        control = hardware_controls[control_id]
        control.assignment = None

        if control_id in control_assignments:
            del control_assignments[control_id]

        return {"message": "Control unassigned successfully"}

    except Exception as e:
        logger.error(f"Error unassigning control: {e}")
        raise HTTPException(status_code=500, detail="Failed to unassign control")


# MIDI Endpoints
@app.get("/api/midi/devices")
async def get_midi_devices():
    """Get available MIDI devices"""
    return {
        "input_devices": midi_input_devices,
        "output_devices": midi_output_devices,
        "current_config": midi_config.dict(),
    }


@app.put("/api/midi/config")
async def update_midi_config(config: MidiConfig):
    """Update MIDI configuration"""
    global midi_config

    try:
        midi_config = config

        # Reinitialize MIDI with new config
        if hardware_manager:
            hardware_manager._init_midi()

        return {"message": "MIDI configuration updated"}

    except Exception as e:
        logger.error(f"Error updating MIDI config: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update MIDI configuration"
        )


@app.post("/api/midi/send")
async def send_midi_message(message: Dict[str, Any]):
    """Send MIDI message"""
    try:
        msg_bytes = message.get("bytes", [])
        if not msg_bytes:
            raise HTTPException(status_code=400, detail="No MIDI bytes provided")

        hardware_manager.send_midi(msg_bytes)

        return {"message": "MIDI message sent"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending MIDI: {e}")
        raise HTTPException(status_code=500, detail="Failed to send MIDI message")


# Display Endpoints
@app.get("/api/display")
async def get_display_content():
    """Get current display content"""
    if not current_display:
        return {"display": None}

    return {"display": asdict(current_display)}


@app.put("/api/display")
async def update_display(display_update: DisplayUpdate):
    """Update display content"""
    try:
        content = DisplayContent(
            title=display_update.title,
            lines=display_update.lines,
            highlight=display_update.highlight,
            timestamp=time.time(),
        )

        hardware_manager.update_display(content)

        return {"message": "Display updated successfully"}

    except Exception as e:
        logger.error(f"Error updating display: {e}")
        raise HTTPException(status_code=500, detail="Failed to update display")


# Simulation Endpoints (for development)
@app.post("/api/simulate/control")
async def simulate_control_change(control_id: str, value: float):
    """Simulate control change (development only)"""
    if not SIMULATE_HARDWARE:
        raise HTTPException(status_code=403, detail="Simulation not enabled")

    try:
        await hardware_manager.simulate_control_change(control_id, value)
        return {"message": f"Simulated {control_id} = {value}"}

    except Exception as e:
        logger.error(f"Error simulating control: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate control")


# Hardware monitoring thread
def hardware_monitor_thread():
    """Hardware monitoring thread (runs in background)"""
    while hardware_running:
        try:
            if not SIMULATE_HARDWARE:
                # Read physical hardware state
                # This would be hardware-specific implementation
                pass

            time.sleep(0.01)  # 100Hz polling rate

        except Exception as e:
            logger.error(f"Hardware monitoring error: {e}")
            time.sleep(1)


# Background tasks
async def hardware_status_monitor():
    """Monitor hardware status and publish updates"""
    while True:
        try:
            await asyncio.sleep(5)  # Every 5 seconds

            if service_bus:
                # Publish hardware status
                status = {
                    "controls": {k: v.value for k, v in hardware_controls.items()},
                    "assignments": control_assignments,
                    "midi_devices": {
                        "input": midi_input_devices,
                        "output": midi_output_devices,
                    },
                    "display": asdict(current_display) if current_display else None,
                }

                await service_bus.publish("hardware_status_update", status)

        except Exception as e:
            logger.error(f"Error in hardware status monitor: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=SERVICE_PORT, reload=False, log_level="info"
    )
