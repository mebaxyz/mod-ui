# 🤖 AI Assistant Setup Prompt

## **Copy and paste this prompt for your next AI interaction:**

---

**Context**: I'm working on the MOD UI project, a modular FastAPI-based web interface for audio effects processing. The project has been fully migrated from legacy Tornado to modern FastAPI architecture with Docker development environment.

**Current Setup**:
- **Architecture**: Modular FastAPI with 6 specialized routers (effects, system, pages, static, data, websocket) 
- **Development Environment**: Docker Compose development setup ONLY (no production configs)
- **Entry Point**: `src/mod_ui/services/api/main.py`
- **Docker Setup**: Use `./scripts/run-modular-docker.sh` to start dev environment
- **Key Endpoints**: Web UI at http://localhost (port 80), API at http://localhost:8888, API docs at http://localhost:8888/docs

**Project Structure**:
```
mod-ui/
├── src/mod_ui/services/api/        # Modern FastAPI application
│   ├── main.py                     # Application entry point  
│   ├── routers/                    # 6 modular routers
│   ├── utils/                      # Shared utilities
│   └── websocket/                  # WebSocket manager
├── scripts/
│   ├── run-modular-docker.sh       # Start development environment
│   └── quick-test-modular.sh       # Quick local testing
├── docs/                           # Documentation
├── docker/
│   └── docker-compose.dev.yml     # Development Docker config
├── mod/                            # Legacy MOD core logic (still used)
├── html/                           # Frontend files
└── utils/                          # C++ utilities for LV2 plugins
```

**Development Workflow**:
1. `source venv/bin/activate` - Activate Python environment
2. `./scripts/run-modular-docker.sh` - Start Docker development environment  
3. Code changes are live-reloaded automatically
4. Web UI: http://localhost, API: http://localhost:8888

**What I need help with**: [Describe what you want to work on]

**Important**: Always use the Docker development environment (`./scripts/run-modular-docker.sh`) for running the application. The FastAPI modular architecture is complete and working.

---

## **Why This Prompt Works**:

✅ **Complete Context**: AI understands the project is migrated and working
✅ **Clear Architecture**: Knows about the 6 modular routers  
✅ **Docker Focus**: Emphasizes using the development environment
✅ **File Structure**: Clear understanding of where things are located
✅ **Working Setup**: AI knows the application is functional and ready

## **Usage Tips**:

1. **Copy the prompt above** and paste it as the first message to your AI assistant
2. **Add your specific question** in the "What I need help with" section
3. **The AI will automatically**:
   - Use the Docker development environment
   - Understand the modular FastAPI structure
   - Work with the correct file paths
   - Know how to test changes (using the endpoints provided)

## **Example Usage**:

Instead of asking: "How do I add a new endpoint?"

Use the full prompt + "What I need help with: I want to add a new API endpoint for managing user presets"

The AI will then:
- Know to work with the appropriate router (probably `effects.py`)
- Use the Docker environment for testing
- Understand the FastAPI patterns already in place
- Test the changes at the correct endpoints

## **Never Need to Explain Again**:
- ✅ FastAPI migration (it's complete!)
- ✅ File structure (clearly documented)  
- ✅ How to run the app (Docker script provided)
- ✅ Where to make changes (router system explained)

**This prompt gives the AI everything it needs to be immediately productive on your project!** 🚀