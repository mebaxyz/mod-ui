# MOD UI Common Service Communication Tests

This directory contains comprehensive tests for the service communication package.

## Test Organization

### **test_service_communication.py** - Core Unit Tests
- Models validation (ServiceRequest, ServiceResponse, etc.)
- ServiceClient basic functionality 
- ServiceServer handler registration
- SimpleService decorator functionality
- **14 tests total** ✅

### **test_integration.py** - Integration Tests  
- Full request-response flow testing
- Error handling and timeout scenarios
- Service client-server interaction
- **Requires Redis for full testing**

### **test_performance.py** - Performance Tests
- Request/response performance measurement
- Concurrent request handling
- Memory usage and cleanup
- Handler registration performance

### **test_config.py** - Configuration Tests
- Environment-specific configurations
- Deployment scenario testing
- Service discovery patterns
- Health checks and versioning

## Running Tests

### **Quick Unit Tests** (No Redis required)
```bash
# Run core unit tests
pytest src/mod_ui/common/tests/test_service_communication.py -v

# Run all unit tests (skips integration tests requiring Redis)
pytest src/mod_ui/common/tests/ -v -k "not integration"
```

### **Full Test Suite** (Requires Redis)
```bash
# Start Redis server first
redis-server

# Run all tests including integration
pytest src/mod_ui/common/tests/ -v
```

### **Specific Test Categories**
```bash
# Performance tests
pytest src/mod_ui/common/tests/test_performance.py -v

# Configuration tests  
pytest src/mod_ui/common/tests/test_config.py -v

# Integration tests (needs Redis)
pytest src/mod_ui/common/tests/test_integration.py -v
```

## Test Coverage

| Component | Unit Tests | Integration | Performance | Config |
|-----------|------------|-------------|-------------|---------|
| Models | ✅ | ✅ | ✅ | ✅ |
| ServiceClient | ✅ | ✅ | ✅ | ✅ |
| ServiceServer | ✅ | ✅ | ⭐ | ✅ |
| SimpleService | ✅ | ✅ | ✅ | ✅ |
| Decorators | ✅ | ⭐ | ✅ | ⭐ |

**Legend:** ✅ Implemented, ⭐ Partial/Future enhancement

## Test Features

### **Mocking Strategy**
- Redis connections mocked for unit tests
- Async operations properly tested
- Error scenarios simulated

### **Performance Benchmarks**
- Request latency measurement
- Concurrent request handling
- Memory usage tracking
- Handler registration speed

### **Environment Testing**
- Development vs Production configs
- Container/Docker scenarios
- High availability patterns
- Service discovery conventions

### **Future Enhancements**
- [ ] Load testing with actual Redis
- [ ] Chaos engineering tests
- [ ] Security testing
- [ ] Monitoring integration tests
- [ ] Cross-service compatibility tests

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- **Fast unit tests** run on every commit
- **Integration tests** run on PRs with Redis service
- **Performance tests** run nightly
- **Configuration tests** validate deployment configs