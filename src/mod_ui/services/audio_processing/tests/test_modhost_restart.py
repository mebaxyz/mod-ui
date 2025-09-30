import asyncio
import os

import pytest

from mod_ui.services.audio_processing.modhost_bridge import ModHostBridge


class MockProcess:
    def __init__(self):
        self._exited = False
        self._killed = False

    def poll(self):
        return 1 if self._exited else None

    def communicate(self, timeout=None):
        return ("", "simulated stderr")

    def terminate(self):
        self._killed = True

    def kill(self):
        self._killed = True


@pytest.mark.asyncio
async def test_modhost_auto_restart(monkeypatch):
    # Ensure we run in non-simulated mode to exercise the monitor
    monkeypatch.setenv("SIMULATE_MODHOST", "false")
    # Faster backoff for tests
    monkeypatch.setenv("MODHOST_RESTART_BACKOFF_BASE", "0.01")
    monkeypatch.setenv("MODHOST_MAX_RESTARTS", "3")

    processes = []

    def popen_factory(*args, **kwargs):
        p = MockProcess()
        processes.append(p)
        return p

    # Make start() immediately consider the host ready
    async def always_ready(self):
        return True

    monkeypatch.setattr("subprocess.Popen", popen_factory)
    # Pretend the mod-host binary exists so start() proceeds
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(ModHostBridge, "_test_connection", always_ready, raising=False)

    bridge = ModHostBridge()

    # Start the bridge; this should create first mock process and a monitor task
    started = await bridge.start()
    assert started is True
    assert len(processes) == 1

    # Allow monitor to start and stabilize
    await asyncio.sleep(0.05)

    # Simulate process exit
    processes[0]._exited = True

    # Wait enough time for monitor to detect exit and attempt a restart
    await asyncio.sleep(0.5 + 0.1)

    # After restart attempt, we should have a restart_count >= 1 and second process created
    assert bridge.restart_count >= 1
    assert len(processes) >= 2

    # Ensure the final process is running (poll returns None)
    assert processes[-1].poll() is None

    # Cleanup
    await bridge.stop()


@pytest.mark.asyncio
async def test_modhost_exceed_max_restarts(monkeypatch):
    # Ensure we run in non-simulated mode to exercise the monitor
    monkeypatch.setenv("SIMULATE_MODHOST", "false")
    # Faster backoff for tests
    monkeypatch.setenv("MODHOST_RESTART_BACKOFF_BASE", "0.005")
    # Limit restarts to 2
    monkeypatch.setenv("MODHOST_MAX_RESTARTS", "2")

    processes = []

    def popen_factory(*args, **kwargs):
        p = MockProcess()
        processes.append(p)
        return p

    # Make start() immediately consider the host ready
    async def always_ready(self):
        return True

    monkeypatch.setattr("subprocess.Popen", popen_factory)
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(ModHostBridge, "_test_connection", always_ready, raising=False)

    bridge = ModHostBridge()

    # Start the bridge; should create first process and monitor
    started = await bridge.start()
    assert started is True

    # Deterministically trigger process exits until monitor exceeds max_restarts
    max_restarts = int(os.getenv("MODHOST_MAX_RESTARTS", "2"))

    # Wait until first process is created
    assert len(processes) >= 1

    # Iteratively mark the latest process as exited and wait for restart_count to increase
    last_count = bridge.restart_count
    while bridge.restart_count <= max_restarts:
        # Mark current process as exited
        processes[-1]._exited = True

        # Wait for restart_count to increment (timeout if monitor fails)
        try:
            await asyncio.wait_for(
                _wait_for_restart_count(bridge, last_count + 1), timeout=1.0
            )
        except asyncio.TimeoutError:
            break

        last_count = bridge.restart_count

    # After monitor finishes, no new processes should be spawned
    before = len(processes)
    await asyncio.sleep(0.2)
    after = len(processes)
    assert before == after

    assert bridge.restart_count >= 1

    await bridge.stop()


async def _wait_for_restart_count(bridge, target):
    """Helper: wait until bridge.restart_count >= target"""
    while bridge.restart_count < target:
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_wait_until_ready_simulation(monkeypatch):
    monkeypatch.setenv("SIMULATE_MODHOST", "true")
    bridge = ModHostBridge()
    # Start simulation so _connected becomes True
    started = await bridge.start()
    assert started is True

    ok = await bridge.wait_until_ready(timeout=1.0)
    assert ok is True

    await bridge.stop()


@pytest.mark.asyncio
async def test_wait_until_ready_timeout(monkeypatch):
    monkeypatch.setenv("SIMULATE_MODHOST", "true")
    bridge = ModHostBridge()
    # don't start the bridge, wait should timeout
    ok = await bridge.wait_until_ready(timeout=0.05)
    assert ok is False
