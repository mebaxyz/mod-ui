#!/bin/bash
set -euo pipefail

# Start a dummy JACK server if one is not available. This uses the 'dummy' backend
# which allows mod-host to register clients without audio hardware. For production
# you should run JACK on the host and mount /dev/snd into the container instead.

echo "Starting dummy JACK server..."
if ! pgrep -x jackd >/dev/null 2>&1; then
  # Run jackd in realtime mode if possible; fallback to non-realtime
  jackd -R -d dummy &
  JACK_PID=$!
  echo "jackd started (pid=$JACK_PID)"
  # Give jack a moment to initialize
  sleep 0.5
fi

echo "Launching mod-host"
exec /src/mod-host/mod-host -n -p 5555 -f 5556
