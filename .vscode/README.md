# VSCode Debugging Setup for MOD UI

This directory contains VSCode configuration files to enable debugging and development of MOD UI directly in VSCode.

## Prerequisites

Make sure you have the following VSCode extensions installed:

1. **Python** (ms-python.python) - Required for Python debugging
2. **Pylint** (ms-python.pylint) - Code linting
3. **Black Formatter** (ms-python.black-formatter) - Code formatting
4. **isort** (ms-python.isort) - Import sorting

## Files Overview

- **`launch.json`** - Debug configurations for running and debugging MOD UI
- **`settings.json`** - VSCode settings for Python development
- **`tasks.json`** - Build tasks for common development operations

## Debug Configurations

### MOD UI Debug Configurations

**Current (Tornado-based):**
1. **MOD UI (Development)** - Run MOD UI with debug logging enabled
2. **MOD UI (Production)** - Run MOD UI in production mode
3. **MOD UI (Custom Port)** - Run on port 8080 with debug logging
4. **MOD UI (All Interfaces)** - Bind to all interfaces (0.0.0.0)

**Future (FastAPI-based - when migration is complete):**
5. **MOD UI (FastAPI - Development)** - Run FastAPI version with debug
6. **MOD UI (FastAPI - Production)** - Run FastAPI version in production
7. **MOD UI (FastAPI - Uvicorn)** - Run with Uvicorn ASGI server

### Testing Configurations

8. **MOD UI Tests** - Run all tests with pytest
9. **MOD UI Test (Current File)** - Run tests for the currently open file

### Utility Configurations

10. **Attach to MOD UI** - Attach debugger to a running MOD UI process
11. **Python: Current File** - Run the currently open Python file

## How to Debug

### Running MOD UI in Debug Mode

**Currently (Tornado-based):**
1. Open the project in VSCode
2. Go to Run → Start Debugging (F5)
3. Select "MOD UI (Development)" from the dropdown
4. VSCode will start MOD UI with debugging enabled
5. Set breakpoints in your code by clicking in the gutter
6. The application will pause at breakpoints

**When FastAPI migration is complete:**
- Use "MOD UI (FastAPI - Development)" for direct module execution
- Use "MOD UI (FastAPI - Uvicorn)" for full ASGI server with auto-reload
- These configurations expect the FastAPI app to be in `src/mod_ui/api/main.py`

### Attaching to Running Process

If you want to debug a process started outside VSCode:

1. Start MOD UI with debugpy enabled (see below)
2. Select "Attach to MOD UI" configuration
3. Click the green play button

To start MOD UI with debugpy:

```bash
pip install debugpy
python -m debugpy --listen 127.0.0.1:5678 --wait-for-client -m mod.webserver run
```

### Running Tests

1. Open a test file or go to Run → Start Debugging
2. Select "MOD UI Tests" or "MOD UI Test (Current File)"
3. Tests will run with debugging enabled

## Environment Variables

The debug configurations set these environment variables:

- `MOD_DEBUG=1` - Enable debug logging
- `MOD_PORT=8888` - Server port (configurable)
- `MOD_HOST=127.0.0.1` - Server host (configurable)

## Tasks

Use Ctrl+Shift+P → "Tasks: Run Task" to access these tasks:

- **Run MOD UI Local** - Run using the local script
- **Install Dependencies** - Install Python requirements
- **Build C++ Utils** - Build the C++ utilities
- **Run Tests** - Run test suite
- **Format Code** - Format with Black
- **Sort Imports** - Sort imports with isort
- **Lint Code** - Lint with Pylint
- **Type Check** - Type check with MyPy
- **Docker Build/Up/Down** - Docker operations

## Troubleshooting

### "Debug type 'python' not recognized"

Install the Python extension:
1. Ctrl+Shift+P → "Extensions: Install Extensions"
2. Search for "Python" and install ms-python.python

### Breakpoints not hit

Make sure:
- You're running the correct debug configuration
- The code is being executed (check the call stack)
- The file is saved and up to date

### Import errors in debugger

The debugger uses the virtual environment automatically. If you see import errors:
1. Make sure the virtual environment is activated
2. Check that dependencies are installed: `pip install -r requirements.txt`
3. Try reloading VSCode: Ctrl+Shift+P → "Developer: Reload Window"

### Port already in use

Change the port in the debug configuration or kill the process using the port:

```bash
# Find process using port 8888
lsof -ti:8888 | xargs kill -9

# Or change port in launch.json
```

## Advanced Debugging

### Conditional Breakpoints

Right-click on a breakpoint and set conditions:
- Expression: `variable_name == "expected_value"`
- Hit Count: Break after N hits
- Log Message: Log without stopping

### Debug Console

Use the Debug Console (Ctrl+Shift+Y) to:
- Evaluate expressions
- Execute Python code
- Inspect variables

### Watch Variables

Add variables to watch in the Variables panel or create watch expressions.

## Remote Debugging

For debugging on remote machines or containers:

1. Install debugpy on the remote machine
2. Start the application with debugpy listening
3. Configure the "Attach to MOD UI" with the remote host/port
4. Attach the debugger

Example remote start:
```bash
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m mod.webserver run
```

## Performance Tips

- Use "Run Without Debugging" (Ctrl+F5) for faster startup
- Disable breakpoints when not needed
- Use conditional breakpoints to avoid stopping on every iteration
- Profile performance with Python's cProfile if needed

## Keyboard Shortcuts

- F5: Start/Continue debugging
- F10: Step over
- F11: Step into
- Shift+F11: Step out
- Shift+F5: Stop debugging
- Ctrl+Shift+F5: Restart debugging

Happy debugging! 🐛