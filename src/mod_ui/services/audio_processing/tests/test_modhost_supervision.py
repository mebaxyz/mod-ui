import asyncio
import os

import pytest

from mod_ui.services.audio_processing import main as audio_main


@pytest.mark.asyncio
async def test_health_includes_modhost_supervision(monkeypatch):
    # Force simulation mode for predictable behavior
    monkeypatch.setenv("SIMULATE_MODHOST", "true")

    # Start service
    await audio_main.startup()

    # Call health via direct handler
    health = await audio_main.handle_health_check()

    assert "details" in health
    modhost = health["details"].get("modhost")
    assert modhost is not None

    # In simulation mode, expected keys exist
    assert "connected" in modhost
    assert "uptime" in modhost
    assert "restart_count" in modhost
    assert "last_error" in modhost

    await audio_main.shutdown()
