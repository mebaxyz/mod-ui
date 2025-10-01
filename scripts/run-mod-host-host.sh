#!/usr/bin/env bash
# Helper to build and run mod-host on the host machine.
# Usage:
#   ./scripts/run-mod-host-host.sh [--no-build] [--foreground] [--dry-run]
# Examples:
#   ./scripts/run-mod-host-host.sh       # build (if needed) and run in foreground
#   ./scripts/run-mod-host-host.sh --no-build --dry-run

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
MODHOST_DIR="$REPO_ROOT/src/mod_ui/services/mod-host"
MODHOST_BIN="$MODHOST_DIR/mod-host"

NO_BUILD=0
FOREGROUND=1
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build) NO_BUILD=1; shift ;;
    --background) FOREGROUND=0; shift ;;
    --foreground) FOREGROUND=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '1,120p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# Commands detection
HAS_PW_JACK=0
if command -v pw-jack >/dev/null 2>&1; then
  HAS_PW_JACK=1
fi

HAS_MAKE=0
if command -v make >/dev/null 2>&1; then
  HAS_MAKE=1
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo "[dry-run] Repository root: $REPO_ROOT"
  echo "[dry-run] mod-host source dir: $MODHOST_DIR"
  echo "[dry-run] Will build: $([[ $NO_BUILD -eq 0 ]] && echo yes || echo no)"
  echo "[dry-run] Use pw-jack: $([[ $HAS_PW_JACK -eq 1 ]] && echo yes || echo no)"
  echo "[dry-run] Run command examples:" 
  if [[ $NO_BUILD -eq 0 ]]; then
    echo "  make -C \"$MODHOST_DIR\" -j\$(nproc)"
  fi
  if [[ $HAS_PW_JACK -eq 1 ]]; then
    echo "  pw-jack \"$MODHOST_BIN\" -n -p 5555 -f 5556"
  else
    echo "  \"$MODHOST_BIN\" -n -p 5555 -f 5556"
  fi
  exit 0
fi

# Check build prerequisites
if [[ $NO_BUILD -eq 0 ]]; then
  if [[ $HAS_MAKE -ne 1 ]]; then
    echo "make is required but not found. Install build-essential and make."
    exit 1
  fi
  echo "Building mod-host (this may take a while)..."
  (cd "$MODHOST_DIR" && make -j"$(nproc)")
fi

if [[ ! -x "$MODHOST_BIN" ]]; then
  echo "mod-host binary not found or not executable: $MODHOST_BIN"
  echo "Try running the script without --no-build to build the project."
  exit 1
fi

# Run using pw-jack if available (connects to PipeWire JACK bridge)
if [[ $HAS_PW_JACK -eq 1 ]]; then
  RUN_CMD=(pw-jack "$MODHOST_BIN" -n -p 5555 -f 5556)
else
  RUN_CMD=("$MODHOST_BIN" -n -p 5555 -f 5556)
fi

echo "Running: ${RUN_CMD[*]}"
if [[ $FOREGROUND -eq 1 ]]; then
  exec "${RUN_CMD[@]}"
else
  "${RUN_CMD[@]}" &
  echo "mod-host started (background pid=$!)"
fi
