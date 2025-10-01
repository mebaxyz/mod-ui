# mod-host in Docker

This folder contains Dockerfiles and a docker-compose snippet to build and run the `mod-host` C/C++ audio engine found in the `src/mod_ui/services/mod-host` submodule.

Prerequisites
- Docker (Engine) and docker-compose installed on your machine.
- If you need real JACK audio device access from within the container, run the container with `/dev/snd` mounted and ensure JACK is available on the host.

Build image

From the repository root run:

```bash
# Build the mod-host image (context is the repo root)
docker compose -f docker/mod-host/docker-compose.yml build
```

Run mod-host

```bash
# Start mod-host in the foreground
docker compose -f docker/mod-host/docker-compose.yml up
```

This will map ports 5555 and 5556 on the host to the container. The default mod-host command runs in non-forking mode and listens on those ports.

Connect audio_processing

Set environment variables so `audio_processing` knows to use the real mod-host:

```bash
export SIMULATE_MODHOST=false
export AUDIO_WAIT_FOR_MODHOST=true
export MODHOST_STARTUP_TIMEOUT=30
# Optionally fail-fast if you prefer:
# export AUDIO_WAIT_FOR_MODHOST_FAILFAST=true
```

Then start the audio_processing service (for example via `./run-local.sh`), and it will connect to the mod-host running in Docker at `localhost:5555`.

Notes
- If you want JACK access inside the container, uncomment the `devices` entry in the compose file and ensure JACK is running on the host.
- Building requires development packages (libjack-dev, liblilv-dev, etc.) which are installed in the build image. For smaller images you can use multi-stage builds and strip build deps (left as an exercise).
