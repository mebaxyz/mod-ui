# MOD UI Migration to FastAPI and Microservices

## Overview

This document outlines the comprehensive modernization plan for MOD UI, transitioning from a monolithic Tornado-based application to a modern FastAPI microservices architecture.

## Current Architecture Issues

### Problems with Current Setup
- **Monolithic Structure**: All functionality in single process
- **Tornado Limitations**: Blocking I/O patterns, limited async support
- **Tight Coupling**: Components heavily interdependent
- **Scalability Issues**: Cannot scale individual components
- **Testing Complexity**: Difficult to test components in isolation
- **Deployment Complexity**: Single point of failure

### Technical Debt
- Mixed concerns in single codebase
- Limited API documentation
- No type safety
- Blocking database/file operations
- Complex state management

## Migration Goals

### Primary Objectives
1. **Replace Tornado with FastAPI**: Modern async web framework
2. **Split into Microservices**: Independent, scalable services
3. **Improve Maintainability**: Better code organization and testing
4. **Enhanced API**: OpenAPI documentation and type safety
5. **Containerization**: Docker-based deployment

### Success Criteria
- All existing functionality preserved
- Improved performance and reliability
- Easier development and testing
- Production-ready deployment pipeline

## Target Architecture

### Service Decomposition

#### 1. API Service (`mod-api`)
**Technology**: FastAPI + Uvicorn
**Responsibilities**:
- REST API endpoints
- WebSocket real-time communication
- Business logic coordination
- Data validation with Pydantic

**Endpoints**:
- `/api/v1/system/*` - System management
- `/api/v1/pedalboard/*` - Pedalboard operations
- `/api/v1/plugins/*` - Plugin management
- `/ws` - WebSocket for real-time updates

#### 2. Web Service (`mod-web`)
**Technology**: Nginx or FastAPI Static Files
**Responsibilities**:
- Serve static web assets (HTML, CSS, JS)
- Template rendering
- Static file caching

#### 3. Hardware Service (`mod-hardware`)
**Technology**: Python asyncio + serial
**Responsibilities**:
- HMI communication
- Hardware state management
- Serial protocol handling

#### 4. Audio Service (`mod-audio`)
**Technology**: Python + JACK
**Responsibilities**:
- LV2 plugin hosting
- Audio processing
- JACK integration

### Shared Components
- **Core Library**: Shared business logic and models
- **Communication Layer**: Inter-service communication
- **Configuration**: Centralized configuration management

## Migration Phases

### Phase 1: Foundation (Week 1-2)
**Objectives**: Set up development environment and basic structure

**Tasks**:
1. Create new directory structure (`src/`, `tests/`, `docker/`, `docs/`)
2. Set up FastAPI project skeleton
3. Create Docker Compose configuration
4. Set up development tooling (pytest, black, mypy)
5. Create basic CI/CD pipeline

**Deliverables**:
- Modern project structure
- Docker development environment
- Basic FastAPI application
- Testing framework

### Phase 2: API Migration (Week 3-4)
**Objectives**: Migrate core API functionality

**Tasks**:
1. Analyze current Tornado endpoints
2. Create FastAPI route handlers
3. Implement Pydantic models
4. Add OpenAPI documentation
5. Create WebSocket endpoints

**Deliverables**:
- Complete API service
- OpenAPI specification
- API tests

### Phase 3: Service Separation (Week 5-6)
**Objectives**: Split monolithic code into services

**Tasks**:
1. Extract hardware communication to separate service
2. Extract audio processing to separate service
3. Create inter-service communication layer
4. Update WebSocket handling for multi-service architecture

**Deliverables**:
- Three independent services
- Service communication protocols
- Integration tests

### Phase 4: Web Interface Migration (Week 7-8)
**Objectives**: Update frontend for new architecture

**Tasks**:
1. Update JavaScript for new API endpoints
2. Modify WebSocket client code
3. Update static file serving
4. Test end-to-end functionality

**Deliverables**:
- Updated web interface
- End-to-end tests
- User acceptance testing

### Phase 5: Production Deployment (Week 9-10)
**Objectives**: Production-ready deployment

**Tasks**:
1. Optimize Docker images
2. Set up production Docker Compose
3. Configure monitoring and logging
4. Performance testing and optimization
5. Documentation completion

**Deliverables**:
- Production deployment configuration
- Monitoring setup
- Performance benchmarks
- Complete documentation

## Technical Implementation Details

### FastAPI Migration

#### Current Tornado Code
```python
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({"status": "ok"})
```

#### New FastAPI Code
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class StatusResponse(BaseModel):
    status: str

@app.get("/api/v1/status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(status="ok")
```

### Service Communication

#### REST API Calls
```python
import httpx

async def get_hardware_status():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://mod-hardware:8001/status")
        return response.json()
```

#### Message Queue (Future)
```python
import aio_pika

async def publish_parameter_change(param_id: str, value: float):
    connection = await aio_pika.connect("amqp://guest:guest@rabbitmq/")
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=f"{param_id}:{value}".encode()),
            routing_key="parameter_changes"
        )
```

### Directory Structure Migration

#### Current Structure
```
mod-ui/
├── mod/
├── html/
├── utils/
├── test/
└── requirements.txt
```

#### New Structure
```
mod-ui/
├── src/
│   └── mod_ui/
│       ├── api/          # FastAPI application
│       ├── core/         # Shared business logic
│       ├── hardware/     # Hardware service
│       ├── audio/        # Audio service
│       └── web/          # Web service
├── tests/
├── docs/
├── docker/
├── scripts/
└── pyproject.toml
```

## Testing Strategy

### Unit Tests
- Individual function/component testing
- Mock external dependencies
- Fast execution for development

### Integration Tests
- Service-to-service communication
- Docker Compose testing
- API contract validation

### End-to-End Tests
- Full application testing
- User journey validation
- Performance testing

### Testing Tools
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client for testing
- **testcontainers**: Docker integration testing

## Deployment Strategy

### Development
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  mod-api:
    build: ./docker/api
    volumes:
      - ./src:/app/src
    environment:
      - DEBUG=1
```

### Production
```yaml
# docker-compose.yml
version: '3.8'
services:
  mod-api:
    image: mebaxyz/mod-api:latest
    environment:
      - ENVIRONMENT=production
  mod-web:
    image: mebaxyz/mod-web:latest
  mod-hardware:
    image: mebaxyz/mod-hardware:latest
    devices:
      - /dev/ttyACM0
  mod-audio:
    image: mebaxyz/mod-audio:latest
    privileged: true
```

## Risk Assessment

### High Risk
- **Real-time Audio Requirements**: Must maintain <10ms latency
- **Hardware Compatibility**: Serial protocol must remain compatible
- **WebSocket Migration**: Real-time features depend on WebSocket support

### Medium Risk
- **Service Communication**: Inter-service calls add complexity
- **Data Consistency**: Distributed state management challenges
- **Deployment Complexity**: Multi-service orchestration

### Mitigation Strategies
- Comprehensive testing of audio latency
- Hardware protocol validation
- Gradual migration with feature flags
- Extensive integration testing

## Success Metrics

### Technical Metrics
- API response time < 100ms
- WebSocket latency < 50ms
- Audio latency < 10ms
- Test coverage > 80%
- Docker image size < 500MB

### Business Metrics
- Development velocity improvement
- Reduced bug reports
- Easier maintenance
- Faster feature delivery

## Rollback Plan

### Phase Rollback
- Each phase designed for independent rollback
- Feature flags for gradual rollout
- Database migration rollback scripts

### Emergency Rollback
- Keep current system running in parallel
- DNS cutover for instant rollback
- Data backup and restore procedures

## Timeline and Milestones

| Phase | Duration | Milestone |
|-------|----------|-----------|
| Foundation | 2 weeks | Development environment ready |
| API Migration | 2 weeks | FastAPI API functional |
| Service Separation | 2 weeks | Microservices operational |
| Web Migration | 2 weeks | Complete UI migration |
| Production | 2 weeks | Production deployment |

## Team Requirements

### Skills Needed
- Python FastAPI development
- Docker and containerization
- Audio programming (JACK, LV2)
- Embedded hardware communication
- Frontend JavaScript development

### Resources Required
- Development environment setup
- Hardware testing devices
- Audio testing equipment
- CI/CD infrastructure

## Conclusion

This migration represents a significant modernization of the MOD UI codebase, moving from a monolithic Tornado application to a scalable FastAPI microservices architecture. The phased approach ensures minimal risk while delivering substantial improvements in maintainability, performance, and developer experience.</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/MIGRATION.md