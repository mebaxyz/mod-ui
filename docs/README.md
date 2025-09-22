# MOD UI - Modern FastAPI Architecture

MOD UI is the web-based user interface for the MOD Duo, a professional guitar multi-effects processor. **This project has been completely modernized** with a FastAPI-based modular architecture, providing a clean, maintainable, and scalable foundation.

🎯 **Status**: **Migration Complete!** Successfully migrated from legacy Tornado to modern FastAPI architecture.

## ✨ Modern Features

- **Modular FastAPI Architecture**: 6 specialized routers for clean separation of concerns
- **Real-time WebSocket Communication**: Modern async WebSocket implementation
- **Docker-First Development**: Complete containerization with dev/prod environments
- **Auto-Generated API Documentation**: Interactive docs at `/docs`
- **Hot Reloading**: Instant code changes during development
- **Modern Python Patterns**: Async/await, type hints, dependency injection

## 🏗️ New Architecture

The modernized MOD UI features a **modular router system**:

### **Core Routers** (`src/mod_ui/services/api/routers/`)
- **`effects.py`** - LV2 plugin management, pedalboard operations
- **`system.py`** - Hardware info, settings, device management  
- **`pages.py`** - HTML page routing and templates
- **`static.py`** - Static file serving (CSS, JS, images)
- **`data.py`** - File operations, screenshots, recordings
- **`websocket.py`** - Real-time WebSocket communications

### **Supporting Components**
- **FastAPI Application**: Modern ASGI web framework
- **WebSocket Manager**: Centralized connection management
- **Template System**: Jinja2 integration for dynamic pages
- **Utility Functions**: Shared logic and helpers
- **Legacy Integration**: Maintains compatibility with existing `mod/` components

## 🚀 Technology Stack

- **Backend**: **FastAPI** (modern Python web framework)
- **Server**: **Uvicorn** ASGI server with hot reloading
- **Frontend**: HTML5, CSS3, JavaScript (existing MOD UI frontend)
- **Audio**: JACK Audio Connection Kit, LV2 plugins (unchanged)
- **Communication**: **Modern WebSockets** with connection management
- **Development**: **Docker** with development and production environments
- **Documentation**: **Auto-generated** OpenAPI/Swagger docs

## Project Structure

```
mod-ui/
├── mod/                    # Core Python modules
│   ├── __init__.py
│   ├── hmi.py             # Hardware interface
│   ├── host.py            # Audio host management
│   ├── session.py         # Session coordination
│   ├── webserver.py       # Web server
│   └── ...
├── html/                  # Web interface files
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── img/
├── default.pedalboard/    # Default pedalboard configuration
├── utils/                 # C++ utilities
└── test/                  # Test files
```

## Getting Started

### Prerequisites

- Python 3.6+
- JACK Audio Connection Kit
- LV2 plugin packages
- MOD Duo hardware (optional for development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mebaxyz/mod-ui.git
cd mod-ui
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Build C++ utilities:
```bash
make -C utils
```

4. Install the package:
```bash
python setup.py install
```

### Running

Start the MOD UI server:
```bash
mod-ui
```

The web interface will be available at `http://localhost:8888`

## Development

### Setting up Development Environment

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Run in development mode:
```bash
python -m mod.webserver
```

### Testing

Run the test suite:
```bash
python -m pytest test/
```

## API Documentation

The MOD UI provides a REST API for programmatic access:

- `GET /system/info` - System information
- `GET /pedalboard/list` - List available pedalboards
- `POST /pedalboard/load` - Load a pedalboard
- `GET /plugins` - List available plugins

See [API Documentation](docs/API.md) for complete API reference.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the AGPL-3.0-or-later license. See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/mebaxyz/mod-ui/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mebaxyz/mod-ui/discussions)

## Migration to FastAPI

This project is currently undergoing modernization to replace the Tornado web framework with FastAPI and split into microservices. See [Migration Guide](docs/MIGRATION.md) for details.</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/README.md