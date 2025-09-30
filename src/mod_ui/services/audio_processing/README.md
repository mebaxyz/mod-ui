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

## Development tasks (atomic, copy to todo)
1. [ ] Implement modhost_bridge.start() that launches mod-host in simulation mode. Acceptance: returns connected True and responds to ping.
2. [ ] Implement ServiceBus method `load_plugin(uri)` → returns instance_id. Acceptance: ServiceBus call returns 200 + instance_id.
3. [ ] Implement ServiceBus method `unload_plugin(instance_id)`. Acceptance: instance removed and resources freed.
4. [ ] Implement `set_parameter(instance_id, symbol, value)` and `get_parameter(...)`. Acceptance: set then get returns same value.
5. [ ] Implement apply_pedalboard(pedalboard_json) that instantiates plugins and sets parameters. Acceptance: publishes `pedalboard_applied` with applied metadata.
6. [ ] Implement connect_ports(source, destination) API. Acceptance: routing graph updated; persists within session.
7. [ ] Add health `/health` endpoint (minimal) exposing: service OK, ServiceBus reachable, mod-host status.
8. [ ] Add simulation mode toggle and configuration (env var). Acceptance: tests run without real mod-host.
9. [ ] Add reconnection logic for mod-host and ServiceBus (exponential backoff). Acceptance: recovers after simulated disconnect.
10. [ ] Add basic metrics (plugin_count, uptime, last_pedalboard_id) and expose via metrics endpoint or health payload.
11. [ ] Write unit tests for modhost_bridge (start/stop/ping), plugin_manager (load/unload), session_manager (apply/save).
12. [ ] Add simple integration test: simulate client -> ServiceBus load plugin -> set param -> verify audio engine event.
13. [ ] Ensure proper graceful shutdown: unload plugins and stop mod-host on SIGTERM.
14. [ ] Linting and CI: add tests + lint to pipeline.

## Notes and tips
- Keep real‑time paths in-process: session_manager should call plugin_manager → audio engine directly without ServiceBus.
- Use ServiceBus only for cross-service RPC/events.
- Use small JSON schema for pedalboards to simplify patch/apply logic during MVP.
- Profile early on target device (Raspberry Pi) and reduce memory footprint (pool sizes, no heavy persistence).

## Next iterations (post-MVP)
- Plugin preset management, parameter automation, MIDI learn, advanced routing UI hooks, sample/IR streaming via File Management service.