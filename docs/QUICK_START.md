# 🚀 MOD UI Quick Start Guide

> **Get up and running in 5 minutes!**

## 🎯 What You'll Have Running
- **Modern FastAPI application** with modular architecture
- **Web UI** at http://localhost:8080  
- **API endpoints** at http://localhost:8888
- **Real-time WebSocket** communication
- **Development environment** with live code reloading

---

## ⚡ Super Quick Start (TL;DR)

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Run development environment  
./scripts/run-modular-docker.sh

# 3. Open browser
# Web UI: http://localhost:8080
# API: http://localhost:8888/ping
```

**Done!** 🎉 Skip to [Testing Your Setup](#-testing-your-setup) to verify everything works.

---

## 📋 Step-by-Step Setup

### **Step 1: Verify Prerequisites**
```bash
# Check Python version (need 3.11+)
python3 --version

# Check if Docker is running
docker --version
docker compose --version

# Check if virtual environment exists
ls venv/
```

### **Step 2: Activate Virtual Environment**
```bash
source venv/bin/activate

# You should see (venv) in your prompt
# (venv) user@computer:~/mod-ui$
```

### **Step 3: Install Dependencies (if needed)**
```bash
# Install Python packages
pip install -r requirements.txt

# Build C++ utilities (required for LV2 plugins)
cd utils && make && cd ..
```

### **Step 4: Choose Your Development Method**

#### **Option A: Docker Development (Recommended)**
```bash
# Start full Docker environment with live reloading
./scripts/run-modular-docker.sh

# Wait for "MOD UI Development Environment is running!" message
```

#### **Option B: Local Development**
```bash
# Quick local test (faster startup)
./scripts/quick-test-modular.sh

# If successful, run the development server
uvicorn src.mod_ui.services.api.main:app --host 0.0.0.0 --port 8888 --reload
```

---

## 🧪 Testing Your Setup

### **1. Health Check**
```bash
# Test API is responding
curl http://localhost:8888/ping

# Expected response:
# {"message": "pong", "status": "healthy"}
```

### **2. System Information**
```bash
# Get system info
curl http://localhost:8888/system/info

# Should return hardware and software information
```

### **3. Web Interface**
Open your browser and visit:
- **Main Web UI**: http://localhost:8080
- **API Documentation**: http://localhost:8888/docs (FastAPI auto-generated)

### **4. WebSocket Test**
```bash
# Visit the WebSocket test page
curl http://localhost:8888/test-websocket

# Or open in browser: http://localhost:8888/test-websocket
```

---

## 🎛️ Available Endpoints

### **Core Web Pages**
- **Main Interface**: http://localhost (port 80)
- **Pedalboard**: http://localhost/pedalboard.html  
- **Settings**: http://localhost/settings.html

### **API Endpoints**
- **Health**: `GET /ping` - http://localhost:8888/ping
- **System Info**: `GET /system/info` - http://localhost:8888/system/info
- **Effects List**: `GET /effect/list` - http://localhost:8888/effect/list
- **API Docs**: `GET /docs` - http://localhost:8888/docs (Interactive documentation)
- **WebSocket**: `WS /websocket` - ws://localhost:8888/websocket

### **File Operations**
- **Screenshots**: `POST /screenshot`
- **Recordings**: Various recording endpoints
- **Static Files**: Automatic serving of CSS, JS, images

---

## 🛠️ Development Workflow

### **Making Code Changes**

#### **With Docker (Recommended)**
1. **Start development environment**: `./scripts/run-modular-docker.sh`
2. **Edit code** in `src/mod_ui/services/api/`
3. **Changes auto-reload** - just refresh browser
4. **View logs**: `docker compose -f docker/docker-compose.dev.yml logs -f`

#### **Local Development**
1. **Start server**: `uvicorn src.mod_ui.services.api.main:app --reload`
2. **Edit code** - server automatically restarts
3. **Test changes** immediately in browser

### **Common Development Tasks**

#### **View Logs**
```bash
# Docker logs
docker compose -f docker/docker-compose.dev.yml logs -f

# Specific service logs
docker compose -f docker/docker-compose.dev.yml logs -f mod-api
```

#### **Restart Services**
```bash
# Restart all Docker services
docker compose -f docker/docker-compose.dev.yml restart

# Restart just the API
docker compose -f docker/docker-compose.dev.yml restart mod-api
```

#### **Stop Everything**
```bash
# Stop Docker services
docker compose -f docker/docker-compose.dev.yml down

# Stop local development server: Ctrl+C
```

#### **Clean Start**
```bash
# Stop everything and rebuild
docker compose -f docker/docker-compose.dev.yml down
docker compose -f docker/docker-compose.dev.yml build --no-cache
./scripts/run-modular-docker.sh
```

---

## 🗂️ File Structure Guide

### **Where to Make Changes**
```
src/mod_ui/services/api/
├── main.py                    # Main application setup
├── routers/
│   ├── effects.py            # Plugin/effect management
│   ├── system.py             # System information
│   ├── pages.py              # HTML page routes  
│   ├── static.py             # Static file serving
│   ├── data.py               # File operations
│   └── websocket.py          # WebSocket handling
├── utils/                     # Shared utilities
└── websocket/                 # WebSocket manager
```

### **Configuration Files**
- **Docker Dev**: `docker/docker-compose.dev.yml`
- **Docker Prod**: `docker/docker-compose.yml`
- **Dependencies**: `requirements.txt`
- **Scripts**: `scripts/` folder

### **Frontend Files**
- **HTML**: `html/` folder
- **CSS**: `html/css/`
- **JavaScript**: `html/js/`
- **Images**: `html/img/`

---

## 🚨 Troubleshooting

### **Common Issues**

#### **"Port already in use"**
```bash
# Kill processes using port 8888
sudo lsof -ti:8888 | xargs kill -9

# Or use different port
uvicorn src.mod_ui.services.api.main:app --port 8889
```

#### **"Module not found"**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check PYTHONPATH
export PYTHONPATH=$(pwd)
```

#### **"Docker build fails"**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild C++ utilities
cd utils && make clean && make && cd ..

# Try again
./scripts/run-modular-docker.sh
```

#### **"WebSocket connection failed"**
- Ensure the API service is running
- Check if port 8888 is accessible
- Verify no firewall blocking connections

### **Getting Help**

#### **Check Container Status**
```bash
docker ps                              # Running containers
docker compose -f docker/docker-compose.dev.yml ps  # Service status
```

#### **Inspect Logs**
```bash
# All services
docker compose -f docker/docker-compose.dev.yml logs

# API service only
docker compose -f docker/docker-compose.dev.yml logs mod-api

# Follow logs live
docker compose -f docker/docker-compose.dev.yml logs -f
```

#### **Test Individual Components**
```bash
# Test FastAPI import
python -c "from src.mod_ui.services.api.main import app; print('✅ Import successful')"

# Test C++ utilities
ls -la utils/libmod_utils.so

# Test Docker connectivity
curl http://localhost:8888/ping
```

---

## 🎯 Next steps

### **You're Ready To:**
1. **Develop new features** by adding routes to existing routers
2. **Add new routers** for new functionality  
3. **Modify the UI** by editing files in `html/`
4. **Add API endpoints** using FastAPI decorators
5. **Test WebSocket features** with real-time communication

### **Explore Further:**
- **API Documentation**: Visit http://localhost:8888/docs for interactive API docs
- **Architecture Details**: Read `docs/MODULAR_ARCHITECTURE_SUMMARY.md`
- **Development Workflow**: Check `docs/DEVELOPMENT_WORKFLOW.md`

---

**🎉 Congratulations!** You now have a fully functional, modern FastAPI-based MOD UI development environment!