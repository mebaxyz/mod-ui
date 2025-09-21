# MOD UI - Musician Operated Device User Interface

MOD UI is the web-based user interface for the MOD Duo, a professional guitar multi-effects processor. This project provides a modern web interface for controlling audio effects, managing pedalboards, and interfacing with the MOD hardware.

## Features

- **Real-time Audio Processing**: Control LV2 audio plugins in real-time
- **Pedalboard Management**: Create, save, and load custom effect chains
- **Hardware Integration**: Direct communication with MOD Duo hardware
- **Web-based Interface**: Modern responsive web UI accessible from any device
- **Plugin Ecosystem**: Support for LADSPA, LV2, and custom MOD plugins

## Architecture

The MOD UI consists of several key components:

- **Web Server**: Serves the web interface and handles HTTP requests
- **HMI (Human-Machine Interface)**: Manages communication with the hardware
- **Host**: Interfaces with the JACK audio system and LV2 plugins
- **Session Manager**: Coordinates between all components
- **WebSocket Server**: Provides real-time communication for the web interface

## Technology Stack

- **Backend**: Python with Tornado web framework
- **Frontend**: HTML5, CSS3, JavaScript with jQuery
- **Audio**: JACK Audio Connection Kit, LV2 plugins
- **Communication**: WebSockets for real-time updates
- **Hardware**: Serial communication with MOD Duo

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