## MADELINE — Madeline Audio Device Orchestrator

MADELINE (Madeline) is a modern fork of the original "mod-audio" project. The fork focuses on:

- migrating service endpoints toward FastAPI for clearer APIs and developer ergonomics,
- opening the platform to custom hardware integrations (modular hardware bridges), and
- improving developer experience with a small test harness and clearer repo layout.

The codebase preserves upstream history. New work will target semantic versioning starting at 1.0.0 for the fork.

Branding and names
- Madeline — friendly, human-facing product name.
- `mado` — recommended short nickname / package/CLI name (Madeline Audio Device Orchestrator).

The rest of this README describes development setup, quickstarts and contribution flow using the `Madeline` brand and the `mado` short name for CLI/package references.

Quick start (development)

Prerequisites

- Python 3.11+ (recommended)
- Virtual environment (venv)
- Optional: Docker (for service composition)

Local dev steps

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Install the package for editable development mode (optional):

```bash
pip install -e .
```

3. Run the local UI and services (convenience script):

```bash
./run-local.sh
```

Running tests

Run the included unit tests quickly:

```bash
python -m pytest -q
```

Repository layout

- `src/mod_ui/` — core services and webserver code
- `docs/` — architecture notes and migration plans
- `docker/` — local docker-compose files and helpers
- `cleanup-archive/` — archived ad-hoc files (ignored by git by default)

Development notes

- The `feature/fastapi-migration` branch contains the active FastAPI migration work. Check service directories for READMEs that outline in-progress tasks.
- Keep changes small and add unit tests for new features. The project has a small test harness and a `run-tests` task in the IDE tasks list.

Contributing

1. Create a branch off `feature/fastapi-migration` for your work.
2. Open a PR with a clear title and description of the change and any migration impact.
3. Keep the changelog entry concise and add docs for breaking changes.

Contact

If you have questions about the migration or hardware integration model, see `docs/ARCHITECTURE.md` and open an issue or PR with proposals.
# MOD Audio System - Consolidated Architecture

## Service Overview

This project uses a consolidated architecture optimized for embedded devices:

1. **[Client Interface Service](services/client_interface/README.md)** - Web UI, API endpoints, WebSocket communication
2. **[System & Resource Management Service](services/system_resource_management/README.md)** - System control, file management, monitoring
3. **[Audio Processing Service](services/audio_processing/README.md)** - Audio engine, plugins, session management
4. **[Hardware Interface Service](services/hardware_interface/README.md)** - Physical controls, displays, MIDI

## Next Implementation Steps

Each service README contains detailed next steps, but here are the high-level priorities:

1. **Complete Core Audio Path** - Ensure audio processing is fully functional
2. **Implement Essential APIs** - Focus on critical control and monitoring endpoints
3. **Add File Management** - Complete file operations and path resolution
4. **Integrate Hardware Controls** - Connect physical controls to audio parameters
5. **Optimize for Embedded** - Fine-tune resource usage for Raspberry Pi

See individual service READMEs for detailed implementation tasks.