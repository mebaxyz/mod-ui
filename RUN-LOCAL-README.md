# MOD UI Local Runner

A convenient script to run MOD UI locally for development and testing.

## Quick Start

```bash
# Run with default settings (port 8888, localhost)
./run-local.sh

# Run with debug logging
./run-local.sh --debug

# Run on a different port
./run-local.sh --port 8080

# Run accessible from other machines
./run-local.sh --host 0.0.0.0
```

## Features

- **Automatic Setup**: Creates virtual environment, installs dependencies, builds C++ utilities
- **Flexible Configuration**: Customize port, host, and debug settings
- **Error Handling**: Checks for missing dependencies and provides helpful error messages
- **Development Friendly**: Optimized for local development with debug options

## Usage

```
./run-local.sh [OPTIONS]

Options:
    -h, --help          Show help message
    -p, --port PORT     Set port number (default: 8888)
    -H, --host HOST     Set host address (default: 127.0.0.1)
    -d, --debug         Enable debug mode with verbose logging
    --no-venv           Skip virtual environment setup
    --no-deps           Skip dependency installation
    --no-build          Skip C++ utilities build
    --production        Run in production mode
```

## Access URLs

Once running, access MOD UI at:
- **Web Interface**: http://localhost:8888 (or your configured host/port)
- **API**: http://localhost:8888/api/v1/

## Examples

```bash
# First time setup (will install everything)
./run-local.sh

# Quick restart (skip setup steps)
./run-local.sh --no-venv --no-deps --no-build

# Debug mode for troubleshooting
./run-local.sh --debug --port 8080

# Production-like setup
./run-local.sh --production --host 0.0.0.0 --port 80
```

## Troubleshooting

If you encounter issues:

1. **Permission denied**: Make sure the script is executable: `chmod +x run-local.sh`
2. **Missing dependencies**: The script will tell you what's missing
3. **Port already in use**: Use `--port` to specify a different port
4. **Build failures**: Check that you have `make` and `gcc` installed

## What the Script Does

1. **Checks system dependencies** (python3, pip3, make, gcc)
2. **Creates/activates virtual environment**
3. **Installs Python dependencies** from requirements.txt
4. **Builds C++ utilities** in the utils/ directory
5. **Installs MOD UI** in development mode
6. **Starts the MOD UI server** with your specified options

The script is idempotent - you can run it multiple times safely.