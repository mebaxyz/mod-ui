#!/usr/bin/env python3
"""
Quick test to verify servicebus package installation and basic functionality
"""

import asyncio

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        from servicebus import Service, ServiceClient, ServiceServer
        from servicebus import ServiceDiscovery, EventBus, MetricsCollector
        from servicebus import handler, event_handler, get_config
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_basic_service():
    """Test basic service creation and functionality"""
    print("Testing basic service creation...")
    
    try:
        from servicebus import Service
        
        # Create service
        service = Service("test-service")
        
        # Register a simple handler
        async def ping_handler(data):
            return {"pong": True, "received": data}
        
        service.register_handler("ping", ping_handler, "Simple ping handler")
        
        print("✅ Service created and handler registered")
        return True
        
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        return False

def test_models():
    """Test model creation"""
    print("Testing models...")
    
    try:
        from servicebus.models import ServiceRequest, ServiceResponse, ServiceEvent, ResponseStatus
        from datetime import datetime
        
        # Test ServiceRequest
        request = ServiceRequest(
            request_id="test-123",
            source_service="client",
            service_name="server", 
            request_type="ping",
            data={"test": True}
        )
        
        # Test ServiceResponse
        response = ServiceResponse(
            request_id="test-123",
            correlation_id="corr-123",
            service_name="test-service",
            status=ResponseStatus.SUCCESS,
            data={"pong": True}
        )
        
        # Test ServiceEvent
        event = ServiceEvent(
            event_type="test.event",
            service_name="test-service",
            timestamp=datetime.utcnow(),
            data={"message": "test"}
        )
        
        print("✅ All models created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Model creation failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("ServiceBus Package Installation Test")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    # Test imports
    if test_imports():
        tests_passed += 1
    
    # Test basic service
    if await test_basic_service():
        tests_passed += 1
    
    # Test models  
    if test_models():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! ServiceBus is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)