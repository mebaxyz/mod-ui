# MOD UI Development Guide

## Overview

This guide provides comprehensive information for developers working on the MOD UI project, including setup instructions, development workflows, coding standards, and testing procedures.

## Development Environment Setup

### Prerequisites

**System Requirements:**
- Linux (Ubuntu 18.04+ recommended)
- Python 3.8+
- 4GB RAM minimum, 8GB recommended
- 10GB free disk space

**Required Software:**
- Git
- Python 3.8+ with pip
- Virtual environment support
- Docker and Docker Compose (for containerized development)
- JACK Audio Connection Kit
- LV2 plugin packages

### Quick Setup

1. **Clone the repository:**
```bash
git clone https://github.com/mebaxyz/mod-ui.git
cd mod-ui
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Build C++ utilities:**
```bash
make -C utils
```

5. **Install in development mode:**
```bash
pip install -e .
```

6. **Verify installation:**
```bash
mod-ui --help
```

### Docker Development Environment

For isolated development:

```bash
# Build development containers
docker-compose -f docker-compose.dev.yml build

# Start development environment
docker-compose -f docker-compose.dev.yml up
```

## Project Structure

```
mod-ui/
├── mod/                    # Core Python modules
│   ├── __init__.py
│   ├── hmi.py             # Hardware interface
│   ├── host.py            # Audio host
│   ├── session.py         # Session management
│   ├── webserver.py       # Web server
│   ├── protocol.py        # Communication protocols
│   ├── addressings.py     # Parameter addressing
│   ├── control_chain.py   # Control chain management
│   ├── development.py     # Development utilities
│   ├── profile.py         # Profiling tools
│   ├── recorder.py        # Recording functionality
│   ├── screenshot.py      # Screenshot utilities
│   ├── settings.py        # Settings management
│   ├── tuner.py           # Tuner functionality
│   └── mod_protocol.py    # MOD protocol implementation
├── html/                  # Web interface
│   ├── *.html            # HTML templates
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   ├── img/              # Images and icons
│   ├── include/          # HTML includes
│   └── resources/        # Additional resources
├── utils/                 # C++ utilities
│   ├── Makefile          # Build configuration
│   ├── *.cpp             # C++ source files
│   ├── *.h               # C++ headers
│   └── sha1/             # SHA1 implementation
├── test/                  # Test files
│   └── hmi-protocol-integrationtest.py
├── default.pedalboard/    # Default pedalboard
│   ├── manifest.ttl      # Pedalboard manifest
│   ├── screenshot.png    # Screenshot
│   └── thumbnail.png     # Thumbnail
├── modtools/             # Python utilities
│   ├── __init__.py
│   ├── pedalboard.py     # Pedalboard utilities
│   ├── tempo.py          # Tempo utilities
│   └── utils.py          # General utilities
└── docs/                 # Documentation
```

## Development Workflow

### Git Workflow

1. **Create feature branch:**
```bash
git checkout -b feature/my-feature
```

2. **Make changes with descriptive commits:**
```bash
git add .
git commit -m "feat: add new parameter validation"
```

3. **Push and create pull request:**
```bash
git push origin feature/my-feature
```

### Code Style

**Python Code Style:**
- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 88 characters (Black formatter default)
- Use type hints where possible

**JavaScript Code Style:**
- Use 2 spaces for indentation
- Use semicolons
- Follow Airbnb JavaScript Style Guide

**Formatting Tools:**
```bash
# Python formatting
pip install black isort
black .
isort .

# JavaScript formatting
npm install -g prettier
prettier --write "html/js/**/*.js"
```

### Commit Message Convention

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

**Examples:**
```
feat(api): add pedalboard save endpoint
fix(hmi): resolve serial communication timeout
docs(readme): update installation instructions
```

## Testing

### Running Tests

**Unit Tests:**
```bash
python -m pytest test/ -v
```

**Integration Tests:**
```bash
python -m pytest test/ -k integration
```

**Coverage Report:**
```bash
python -m pytest --cov=mod --cov-report=html
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from mod.session import Session

class TestSession:
    def test_initialization(self):
        session = Session()
        assert session.state == "initialized"

    def test_parameter_addressing(self):
        session = Session()
        address = session.get_parameter_address("amp", "gain")
        assert address is not None
```

**Integration Test Example:**
```python
import pytest
from mod.hmi import HMI
from mod.host import Host

class TestHMIAudioIntegration:
    def test_parameter_sync(self):
        hmi = HMI()
        host = Host()

        # Set parameter via HMI
        hmi.set_parameter("amp", "gain", 0.8)

        # Verify host received the change
        assert host.get_parameter("amp", "gain") == 0.8
```

### Test Coverage Goals

- **Unit Tests:** > 80% coverage
- **Integration Tests:** All major workflows covered
- **End-to-End Tests:** Critical user journeys

## Debugging

### Logging

MOD UI uses Python's logging module with different levels:

```python
import logging

logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Error conditions
- `CRITICAL`: Critical errors

### Debug Mode

Run with debug logging:
```bash
MOD_DEBUG=1 mod-ui
```

### Profiling

**CPU Profiling:**
```python
import cProfile
cProfile.run('main()', 'profile_output.prof')
```

**Memory Profiling:**
```python
from memory_profiler import profile

@profile
def my_function():
    # Code to profile
    pass
```

### Common Debugging Issues

**Audio Issues:**
- Check JACK status: `jackd --version`
- Verify LV2 plugins: `lv2ls`
- Check audio device permissions

**Serial Communication:**
- Verify device permissions: `ls -la /dev/ttyACM*`
- Check serial port: `dmesg | grep tty`

**Web Interface:**
- Check browser console for JavaScript errors
- Verify WebSocket connection
- Check network tab for failed requests

## Performance Optimization

### Audio Performance

**Latency Requirements:**
- Audio processing: < 10ms latency
- UI response: < 100ms
- Hardware communication: < 50ms

**Optimization Techniques:**
- Use real-time threads for audio processing
- Minimize memory allocations in audio callbacks
- Cache frequently used data
- Use efficient data structures

### Memory Management

**Best Practices:**
- Avoid memory leaks in long-running processes
- Use weak references for callbacks
- Clean up resources properly
- Monitor memory usage regularly

### Profiling Tools

```bash
# Install profiling tools
pip install memory-profiler line-profiler

# Profile specific function
@profile
def audio_callback():
    # Audio processing code
    pass
```

## Hardware Development

### MOD Duo Hardware

**Specifications:**
- ARM Cortex-A9 processor
- 512MB RAM
- Serial communication at 115200 baud
- Custom HMI protocol

**Development Setup:**
1. Connect MOD Duo via USB
2. Verify serial device: `/dev/ttyACM0`
3. Set proper permissions: `sudo chmod 666 /dev/ttyACM0`

### Protocol Documentation

**HMI Protocol:**
- Binary protocol over serial
- Message format: `[HEADER][PAYLOAD][CHECKSUM]`
- Real-time parameter updates
- Hardware status monitoring

**Example Message:**
```
Header: 0xAA 0x55 (sync bytes)
Type: 0x01 (parameter update)
Length: 0x08
Data: [param_id][value_high][value_low]
Checksum: CRC8
```

## Web Development

### Frontend Architecture

**Technology Stack:**
- HTML5 with semantic markup
- CSS3 with responsive design
- Vanilla JavaScript (no frameworks)
- WebSocket for real-time updates
- Canvas API for visual components

**File Structure:**
```
html/
├── index.html          # Main page
├── pedalboard.html     # Pedalboard editor
├── settings.html       # Settings page
├── css/
│   ├── main.css       # Main styles
│   ├── dashboard.css  # Dashboard styles
│   └── pedals.css     # Pedal styles
├── js/
│   ├── main.js        # Main application
│   ├── websocket.js   # WebSocket client
│   └── utils.js       # Utility functions
└── img/               # Images and icons
```

### JavaScript Best Practices

**Code Organization:**
```javascript
// Module pattern
const PedalboardManager = (function() {
    let currentPedalboard = null;

    function loadPedalboard(id) {
        // Implementation
    }

    function savePedalboard() {
        // Implementation
    }

    return {
        loadPedalboard,
        savePedalboard
    };
})();
```

**Error Handling:**
```javascript
try {
    websocket.send(message);
} catch (error) {
    console.error('WebSocket error:', error);
    // Reconnection logic
}
```

**Performance:**
- Minimize DOM manipulations
- Use event delegation
- Cache DOM queries
- Debounce user input

## API Development

### REST API Guidelines

**Endpoint Naming:**
- Use nouns for resources: `/pedalboards`, `/plugins`
- Use HTTP methods appropriately:
  - `GET` for retrieval
  - `POST` for creation
  - `PUT` for updates
  - `DELETE` for removal

**Response Format:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message",
  "error": "Error message if success is false"
}
```

### WebSocket API

**Connection Management:**
```javascript
const ws = new WebSocket('ws://localhost:8888/ws');

ws.onopen = function(event) {
    console.log('WebSocket connected');
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    handleMessage(message);
};

ws.onclose = function(event) {
    console.log('WebSocket disconnected');
    // Reconnection logic
};
```

**Message Types:**
- `parameter_changed`: Parameter value updates
- `pedalboard_changed`: Pedalboard modifications
- `hardware_event`: Hardware input events
- `status_update`: System status changes

## Deployment

### Local Development
```bash
# Run directly
mod-ui

# Run with debug logging
MOD_DEBUG=1 mod-ui

# Run with custom port
mod-ui --port 8080
```

### Docker Deployment
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f mod-ui
```

### Production Deployment

**System Requirements:**
- Ubuntu Server 18.04+
- 2GB RAM minimum
- JACK Audio Connection Kit
- LV2 plugins installed

**Installation Steps:**
1. Install system dependencies
2. Clone repository
3. Build and install
4. Configure systemd service
5. Start service

## Contributing

### Pull Request Process

1. **Fork and clone:**
```bash
git clone https://github.com/yourusername/mod-ui.git
```

2. **Create feature branch:**
```bash
git checkout -b feature/amazing-feature
```

3. **Make changes and tests**

4. **Run tests:**
```bash
python -m pytest
```

5. **Update documentation**

6. **Commit and push:**
```bash
git add .
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature
```

7. **Create pull request**

### Code Review Guidelines

**Checklist:**
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes without discussion
- [ ] Performance impact assessed
- [ ] Security implications reviewed

### Release Process

1. **Version bump:** Update version in `setup.py`
2. **Changelog:** Update `CHANGELOG`
3. **Tag release:** `git tag v1.13.0`
4. **Build packages:** `python setup.py sdist bdist_wheel`
5. **Publish:** Upload to PyPI

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Reinstall package
pip uninstall mod-ui
pip install -e .
```

**Audio Issues:**
```bash
# Check JACK status
jackd -S

# List LV2 plugins
lv2ls
```

**Permission Issues:**
```bash
# Fix serial device permissions
sudo usermod -a -G dialout $USER
# Logout and login again
```

**WebSocket Issues:**
- Check firewall settings
- Verify port availability
- Check browser network tab

### Getting Help

**Resources:**
- [GitHub Issues](https://github.com/mebaxyz/mod-ui/issues)
- [Documentation](docs/)
- [Community Forum](https://forum.moddevices.com)

**Debug Information:**
When reporting issues, include:
- MOD UI version
- Python version
- Operating system
- Hardware details
- Full error logs
- Steps to reproduce

## Future Development

### Planned Features

**Short Term:**
- FastAPI migration
- Microservices architecture
- Improved testing framework

**Long Term:**
- Modern web UI (React/Vue)
- Plugin marketplace
- Cloud synchronization
- Mobile app

### Technology Upgrades

**Python Modernization:**
- Type hints throughout codebase
- Async/await patterns
- Pydantic for data validation

**Frontend Modernization:**
- Modern JavaScript (ES6+)
- Component-based architecture
- Progressive Web App features

**Infrastructure:**
- Docker containerization
- Kubernetes orchestration
- CI/CD pipelines
- Monitoring and logging

This development guide will be updated as the project evolves. Check back regularly for the latest information.</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/DEVELOPMENT.md