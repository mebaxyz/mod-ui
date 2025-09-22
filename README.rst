MOD UI - Modern FastAPI Architecture
====================================

This is the UI for the MOD software. It's a modern **FastAPI-based webserver** that delivers an HTML5 interface and communicates with mod-host.
It features a **modular architecture** with specialized routers, Docker support, and real-time WebSocket communication.

🎯 **Project Status**: **Migration Complete!** The project has been successfully migrated from legacy Tornado to modern FastAPI architecture.

✨ **Quick Start**: See ``docs/QUICK_START.md`` for immediate setup instructions.
📋 **Project Status**: See ``docs/PROJECT_STATUS.md`` if returning after a break.

Quick Setup
-----------

⚡ **Super Quick Start**::

    $ source venv/bin/activate
    $ ./scripts/run-modular-docker.sh
    # Open http://localhost:8080

📋 **Prerequisites**:
- Python 3.11+
- Docker & Docker Compose  
- Virtual environment already set up

📦 **System Dependencies** (if needed)::

    $ sudo apt-get install python3-pip python3-dev git build-essential libasound2-dev libjack-jackd2-dev liblilv-dev libjpeg-dev zlib1g-dev

🐳 **Development Setup**::

    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ cd utils && make && cd ..
    $ ./scripts/run-modular-docker.sh

For detailed instructions, see ``docs/QUICK_START.md``.

Modern Architecture
------------------

🏗️ **Modular FastAPI Design**:
- **6 specialized routers**: effects, system, pages, static, data, websocket
- **Hardware service**: Standalone microservice for device management
- **Real-time communication**: WebSocket support + Redis pub/sub
- **Modern Python**: FastAPI with async/await  
- **Docker ready**: Development and production containers
- **API documentation**: Auto-generated at ``/docs``

📁 **Project Structure**::

    mod-ui/
    ├── src/mod_ui/services/api/        # Modern FastAPI application
    │   ├── main.py                     # Application entry point
    │   ├── routers/                    # Modular routers (6 modules)
    │   ├── utils/                      # Shared utilities  
    │   └── websocket/                  # WebSocket manager
    ├── scripts/                        # Executable scripts
    │   ├── run-modular-docker.sh       # Development environment
    │   ├── run-production-docker.sh    # Production deployment
    │   └── quick-test-modular.sh       # Quick local testing
    ├── docs/                           # Documentation
    │   ├── PROJECT_STATUS.md           # Current project state
    │   ├── QUICK_START.md              # Step-by-step setup
    │   └── *.md                        # Architecture docs
    └── docker/                         # Docker configurations

Run Options  
-----------

🐳 **Docker Development** (Recommended)::

    $ ./scripts/run-modular-docker.sh
    # Web UI: http://localhost:8080
    # API: http://localhost:8888

🖥️ **Local Development**::

    $ source venv/bin/activate
    $ uvicorn src.mod_ui.services.api.main:app --host 0.0.0.0 --port 8888 --reload

🏭 **Production Deployment**::

    $ ./scripts/run-production-docker.sh

🧪 **Quick Test**::

    $ ./scripts/quick-test-modular.sh

Available Endpoints
------------------

- **Web UI**: http://localhost:8080
- **API Health**: http://localhost:8888/ping  
- **System Info**: http://localhost:8888/system/info
- **Effects List**: http://localhost:8888/effect/list
- **API Docs**: http://localhost:8888/docs (Interactive)
- **WebSocket**: ws://localhost:8888/websocket

Documentation
-----------

📖 **Essential Reading**:
- ``docs/PROJECT_STATUS.md`` - Current state and what's been accomplished
- ``docs/QUICK_START.md`` - Step-by-step setup guide  
- ``docs/MODULAR_ARCHITECTURE_SUMMARY.md`` - Technical architecture details
- ``docs/HARDWARE_SERVICE.md`` - Hardware microservice documentation
- ``docs/ARCHITECTURE.md`` - Complete system architecture

🔧 **For Developers**:
- All scripts moved to ``scripts/`` folder
- All documentation in ``docs/`` folder
- Modern FastAPI patterns throughout
- Docker development workflow established
