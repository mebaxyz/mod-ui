# 🔧 Development Workflow

> **Your complete guide for developing with the MOD UI modular FastAPI architecture**

## 🎯 Development Philosophy

The MOD UI project now uses a **modular FastAPI architecture** designed for:
- **Easy development** with hot reloading
- **Clear separation** of concerns via routers
- **Docker-first** development workflow
- **Modern Python** patterns and best practices

---

## 🚀 Getting Started

### **Daily Development Workflow**
```bash
# 1. Activate environment
source venv/bin/activate

# 2. Start development environment
./scripts/run-modular-docker.sh

# 3. Open browser to http://localhost:8080
# 4. Edit code, changes auto-reload
# 5. Test and iterate
```

### **Development Environment**
- **Web UI**: http://localhost:8080 (Nginx + static files)
- **API**: http://localhost:8888 (FastAPI with live reload)
- **API Docs**: http://localhost:8888/docs (Auto-generated)
- **WebSocket**: ws://localhost:8888/websocket

---

## 🏗️ Project Architecture

### **Modular Router System**
```
src/mod_ui/services/api/routers/
├── effects.py      # LV2 plugins, pedalboard operations
├── system.py       # Hardware info, settings, device management
├── pages.py        # HTML page routing and templates
├── static.py       # Static file serving (CSS, JS, images)
├── data.py         # File operations, screenshots, recordings
└── websocket.py    # Real-time WebSocket communications
```

### **Key Components**
- **Entry Point**: `src/mod_ui/services/api/main.py`
- **Shared Utils**: `src/mod_ui/services/api/utils/`
- **WebSocket Manager**: `src/mod_ui/services/api/websocket/`
- **Templates**: Jinja2 templates in utils
- **Legacy Integration**: `mod/` folder (still used for core logic)

---

## 🛠️ Common Development Tasks

### **Adding New API Endpoints**

#### **1. Choose the Right Router**
- **Effects**: Plugin/pedalboard related → `routers/effects.py`
- **System**: Hardware/settings → `routers/system.py`  
- **Pages**: HTML pages → `routers/pages.py`
- **Data**: File operations → `routers/data.py`
- **WebSocket**: Real-time features → `routers/websocket.py`

#### **2. Add Your Endpoint**
```python
# Example: Adding to effects.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter()

@router.get("/effects/custom-endpoint")
async def get_custom_data() -> Dict[str, Any]:
    """Your new endpoint description"""
    try:
        # Your logic here
        return {"status": "success", "data": "your_data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### **3. Test Your Endpoint**
```bash
# Test with curl
curl http://localhost:8888/effects/custom-endpoint

# Or visit http://localhost:8888/docs for interactive testing
```

### **Adding New HTML Pages**

#### **1. Create HTML Template**
```html
<!-- html/your-page.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Your Page</title>
    <link rel="stylesheet" href="/css/main.css">
</head>
<body>
    <h1>Your Content</h1>
    <script src="/js/main.js"></script>
</body>
</html>
```

#### **2. Add Route in pages.py**
```python
@router.get("/your-page")
async def your_page(request: Request):
    """Serve your custom page"""
    return templates.TemplateResponse(
        "your-page.html", 
        {"request": request}
    )
```

### **WebSocket Development**

#### **1. Server-Side (websocket.py)**
```python
@router.websocket("/ws/custom")
async def custom_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process data
            await manager.send_personal_message(
                f"Processed: {data}", websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

#### **2. Client-Side JavaScript**
```javascript
const ws = new WebSocket('ws://localhost:8888/ws/custom');
ws.onmessage = function(event) {
    console.log('Received:', event.data);
};
ws.send('Hello Server');
```

---

## 🐳 Docker Development

### **Development vs Production**

#### **Development Mode** (`docker-compose.dev.yml`)
```bash
./scripts/run-modular-docker.sh
```
- ✅ **Live code reloading** - changes reflected immediately
- ✅ **Debug logging** enabled  
- ✅ **Volume mounts** for all source code
- ✅ **Development optimizations**

#### **Production Mode** (`docker-compose.yml`)
```bash
./scripts/run-production-docker.sh  
```
- ✅ **Optimized builds** with minimal layers
- ✅ **Read-only code** copied into containers
- ✅ **Production settings** (no debug)
- ✅ **Health checks** and monitoring

### **Docker Commands Reference**

#### **Service Management**
```bash
# View running containers
docker compose -f docker/docker-compose.dev.yml ps

# View all logs
docker compose -f docker/docker-compose.dev.yml logs

# Follow API logs specifically  
docker compose -f docker/docker-compose.dev.yml logs -f mod-api

# Restart specific service
docker compose -f docker/docker-compose.dev.yml restart mod-api

# Stop all services
docker compose -f docker/docker-compose.dev.yml down
```

#### **Debugging Containers**
```bash
# Execute command in running container
docker compose -f docker/docker-compose.dev.yml exec mod-api bash

# View container resource usage
docker stats

# Inspect container configuration
docker compose -f docker/docker-compose.dev.yml config
```

#### **Clean Rebuild**
```bash
# Stop and remove everything
docker compose -f docker/docker-compose.dev.yml down --volumes --remove-orphans

# Rebuild from scratch
docker compose -f docker/docker-compose.dev.yml build --no-cache

# Start fresh
./scripts/run-modular-docker.sh
```

---

## 🧪 Testing

### **Manual Testing**

#### **API Health Checks**
```bash
# Basic health check
curl http://localhost:8888/ping

# System information  
curl http://localhost:8888/system/info

# Effects list
curl http://localhost:8888/effect/list

# Test with pretty output
curl -s http://localhost:8888/ping | jq .
```

#### **WebSocket Testing**
```bash
# Visit WebSocket test page
curl http://localhost:8888/test-websocket

# Or open in browser for interactive testing
open http://localhost:8888/test-websocket
```

#### **Frontend Testing**
- **Main UI**: http://localhost:8080
- **Pedalboard**: http://localhost:8080/pedalboard.html
- **Settings**: http://localhost:8080/settings.html

### **Automated Testing**
```bash
# Run quick validation
./scripts/quick-test-modular.sh

# Test Docker setup
docker compose -f docker/docker-compose.dev.yml config

# Validate C++ utilities
ls -la utils/libmod_utils.so
```

---

## 🐛 Debugging

### **Common Issues & Solutions**

#### **"Connection Refused" Errors**
```bash
# Check if containers are running
docker ps

# Check port conflicts
sudo lsof -i :8888
sudo lsof -i :8080

# Restart Docker services
docker compose -f docker/docker-compose.dev.yml restart
```

#### **"Module Not Found" Errors**
```bash
# Verify virtual environment
source venv/bin/activate
which python

# Check PYTHONPATH in container
docker compose -f docker/docker-compose.dev.yml exec mod-api env | grep PYTHON

# Reinstall dependencies
pip install -r requirements.txt
```

#### **C++ Utilities Issues**
```bash
# Rebuild utilities
cd utils && make clean && make && cd ..

# Check library exists
ls -la utils/libmod_utils.so

# Verify library path in container
docker compose -f docker/docker-compose.dev.yml exec mod-api ls -la /app/utils/
```

### **Debug Mode**

#### **Enable Verbose Logging**
```python
# In your router file
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.get("/debug-endpoint")
async def debug_endpoint():
    logger.debug("This is a debug message")
    return {"debug": "enabled"}
```

#### **FastAPI Debug Mode**
```bash
# Run with debug and reload
uvicorn src.mod_ui.services.api.main:app --host 0.0.0.0 --port 8888 --reload --log-level debug
```

---

## 📈 Performance Optimization  

### **FastAPI Best Practices**
- ✅ Use `async def` for I/O operations
- ✅ Use `def` for CPU-bound operations  
- ✅ Implement proper error handling
- ✅ Add response models for type safety
- ✅ Use dependency injection for shared resources

### **Docker Optimization**
- ✅ Multi-stage builds for production
- ✅ Minimal base images (python:3.11-slim)
- ✅ Proper layer caching
- ✅ Health checks for reliability

---

## 🔄 Code Organization

### **Router Guidelines**
```python
# Good router structure
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/endpoint", response_model=YourModel)
async def your_endpoint(
    param: str,
    common_dep: CommonType = Depends(get_common_dependency)
) -> YourModel:
    """Clear docstring describing the endpoint"""
    try:
        logger.info(f"Processing request: {param}")
        result = await your_async_operation(param)
        return YourModel(**result)
    except SpecificException as e:
        logger.error(f"Specific error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### **File Organization**
```
your_feature/
├── __init__.py
├── models.py          # Pydantic models
├── routes.py          # FastAPI routes  
├── service.py         # Business logic
├── utils.py           # Helper functions
└── tests/
    ├── test_routes.py
    └── test_service.py
```

---

## 🚀 Deployment

### **Development Deployment**
```bash
# Start development environment
./scripts/run-modular-docker.sh

# Access services
# - Web UI: http://localhost:8080  
# - API: http://localhost:8888
# - Docs: http://localhost:8888/docs
```

### **Production Deployment**
```bash
# Production environment
./scripts/run-production-docker.sh

# Monitor services
docker compose -f docker/docker-compose.yml logs -f

# Scale services (if needed)
docker compose -f docker/docker-compose.yml up --scale mod-api=2
```

---

## 📚 Learning Resources

### **FastAPI**
- **Official Docs**: https://fastapi.tiangolo.com/
- **Interactive API Docs**: http://localhost:8888/docs (when running)
- **Alternative Docs**: http://localhost:8888/redoc

### **Project Documentation**
- **Project Status**: `docs/PROJECT_STATUS.md`
- **Quick Start**: `docs/QUICK_START.md`  
- **Architecture**: `docs/MODULAR_ARCHITECTURE_SUMMARY.md`
- **Migration History**: `docs/FASTAPI_MIGRATION_PROGRESS.md`

---

**Happy Coding!** 🎉 The modular architecture makes development clean, fast, and enjoyable!