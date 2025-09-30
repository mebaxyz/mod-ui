# Audio Processing Service (MVP)

## Purpose
Core real‑time audio engine: plugin hosting, parameter control, session application and mod-host bridge. This is the highest priority — other services depend on it.

## Scope for MVP
- Stable mod‑host bridge start/stop and IPC
- Load/unload plugin instances
- Set/get parameter values
- Apply pedalboard/session snapshot to engine
- Minimal audio routing (connect ports)
- Health endpoint + basic metrics
- Simulation mode for local dev

## Constraints
- Prioritize low latency and reliability.
- Keep blocking operations out of startup lifespan; init heavy tasks after HTTP is live.
- Internal service: no HTTP exposed besides a minimal health endpoint; all control via ServiceBus RPC/events.

## MVP Acceptance Criteria
- mod-host process starts and responds to a simple ping RPC.
- Plugins can be loaded/unloaded and report instance IDs.
- Parameter set/get roundtrip completes in <50ms in simulation.
- Applying a saved pedalboard updates engine state and publishes `pedalboard_applied` event.
- Health endpoint `/health` returns OK and ServiceBus connectivity status.
- Unit/integration tests cover the above flows.

## Files to implement
- main.py — service bootstrap, ServiceBus registration, health
- modhost_bridge.py — manage mod-host lifecycle and RPC
- plugin_manager.py — load/unload, parameter mapping, persistence hooks
- session_manager.py — apply/save pedalboards, snapshot handling
- routing.py — connect_ports API, basic routing graph
- tests/ — unit + integration tests (simulate mod-host)

## Development tasks (status)

Completed (as of 2025-09-30)
- Implemented a ZeroMQ-based ServiceBus RPC/PubSub replacement and typed message models.
- ModHost bridge: `modhost_bridge.py` supports start/stop (simulation mode available), ping/health, supervision with restart/backoff, and exposes status fields (restart_count, last_error, uptime).
- Startup helpers: `wait_until_ready()` and `start_and_wait(timeout)` to optionally block until mod-host is responsive.
- Pedalboard persistence: disk-backed save/list/load/delete plus export/import with a schema version field and atomic writes.
- Service wiring: `main.py` registers RPC handlers for persistence and import/export; audio_processing wired to use ModHostBridge, PluginManager and SessionManager handlers.
- Tests: pytest + pytest-asyncio tests added for mod-host supervision, restart behavior, wait/start semantics, and pedalboard persistence (all run locally and pass in simulation mode).
- Simulation mode: `SIMULATE_MODHOST` support for fast, deterministic tests.

Partially completed / in-progress
- Health: health/healthcheck routed via ServiceBus RPC; if you also need an HTTP /health endpoint in every deployment we can add one (current design exposes health via ServiceBus handlers).
- Metrics: runtime status fields (uptime, restart_count, last_error) are exposed; additional metrics (plugin_count, last_pedalboard_id) can be added on request.
- Lint/static: targeted lint fixes applied; some design-level pylint messages remain intentionally deferred and can be cleaned up in a dedicated refactor pass.

Remaining tasks (actionable next steps)
- Confirm and document desired default for `AUDIO_WAIT_FOR_MODHOST` (current behavior: startup blocks when enabled). Option: make waiting non-fatal (warn only) or default to false for faster startup.
- Add/verify full graceful shutdown across all platforms (ensure SIGTERM handler unloads plugins and stops mod-host cleanly in production deployments).
- Expand metrics: add `plugin_count`, `last_pedalboard_id`, and expose via a metrics endpoint or enrich the health payload.
- Routing API: implement or complete `connect_ports(source, destination)` and persist routing graph in session storage if needed.
- Finish any remaining PluginManager feature gaps (if load/unload/set/get parameter APIs are incomplete) and add targeted tests.
- CI integration: add the new tests and lint checks to the repository CI pipeline and ensure they run in simulation mode for speed.
- Optional: make the mod-host wait behavior softer (log + continue) and add a configuration flag to fail-fast vs. warn-and-continue.

New configuration
- AUDIO_WAIT_FOR_MODHOST_FAILFAST (env): when true and `AUDIO_WAIT_FOR_MODHOST` is enabled, the service will abort startup if the mod-host does not become ready within `MODHOST_STARTUP_TIMEOUT`. Default: false (keep current warn-and-continue behavior).

Configuration / runtime notes
- AUDIO_WAIT_FOR_MODHOST (env): when true the service will start the mod-host and wait up to `MODHOST_STARTUP_TIMEOUT` seconds for it to respond. NOTE: wait is now non-fatal — if the mod-host fails to become ready within the timeout the service will continue startup but will log a warning.
- MODHOST_STARTUP_TIMEOUT (env): seconds (float) to wait for mod-host readiness; empty or unset means indefinite wait when waiting is enabled.
- SIMULATE_MODHOST (env): when true the ModHostBridge will run in simulation mode (fast, deterministic) used by tests and local dev.
- AUDIO_PROCESSING_DATA_DIR (env): directory used by the storage module for pedalboards. Defaults to ./data/audio_processing inside the repo when unset.

If you prefer fail-fast behavior (raise on mod-host timeout) we can revert the non-fatal change and make it configurable; tell me your preference.

## Notes and tips
- Keep real‑time paths in-process: session_manager should call plugin_manager → audio engine directly without ServiceBus.
- Use ServiceBus only for cross-service RPC/events.
- Use small JSON schema for pedalboards to simplify patch/apply logic during MVP.
- Profile early on target device (Raspberry Pi) and reduce memory footprint (pool sizes, no heavy persistence).

## Next iterations (post-MVP)
- Plugin preset management, parameter automation, MIDI learn, advanced routing UI hooks, sample/IR streaming via File Management service.