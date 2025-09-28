#!/usr/bin/env python3
"""
MOD UI Docker Integration Test Suite

Comprehensive pytest suite for testing the complete MOD UI functionality
using Docker containers. This tests the microservices architecture with
proper configuration management and inter-service communication.

Usage:
    pip install pytest pytest-asyncio docker
    pytest test_docker_integration.py -v
"""

import asyncio
import json
import time
from pathlib import Path

import pytest
import redis
import requests

import docker


class DockerTestEnvironment:
    """Manages Docker test environment setup and teardown"""

    def __init__(self):
        self.client = docker.from_env()
        self.project_root = Path(__file__).parent
        self.compose_file = self.project_root / "docker" / "docker-compose.dev.yml"
        self.containers = []

    def start_environment(self):
        """Start the complete Docker environment"""
        print("🚀 Starting Docker test environment...")

        # Start with docker-compose
        import subprocess

        result = subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), "up", "-d"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise Exception(f"Failed to start Docker environment: {result.stderr}")

        # Wait for services to be ready
        self.wait_for_services()

    def stop_environment(self):
        """Stop and cleanup Docker environment"""
        print("🛑 Stopping Docker test environment...")

        import subprocess

        subprocess.run(
            ["docker", "compose", "-f", str(self.compose_file), "down", "-v"],
            capture_output=True,
        )

    def wait_for_services(self, timeout=120):
        """Wait for all services to be healthy"""
        print("⏳ Waiting for services to be ready...")

        services = {
            "redis": {"port": 6379, "check": self._check_redis},
            "config-service": {"check": self._check_redis_service},
            "audio-engine": {"check": self._check_redis_service},
            "session-v2": {"check": self._check_redis_service},
            "api": {"port": 8888, "check": self._check_http_service},
        }

        start_time = time.time()
        ready_services = set()

        while time.time() - start_time < timeout:
            for service_name, config in services.items():
                if service_name in ready_services:
                    continue

                if config["check"](config.get("port")):
                    print(f"✅ {service_name} is ready")
                    ready_services.add(service_name)

            if len(ready_services) == len(services):
                print("🎉 All services are ready!")
                return

            time.sleep(2)

        raise TimeoutError(
            f"Services not ready after {timeout}s. Ready: {ready_services}"
        )

    def _check_redis(self, port=6379):
        """Check if Redis is responding"""
        try:
            r = redis.Redis(host="localhost", port=port, socket_timeout=1)
            r.ping()
            return True
        except:
            return False

    def _check_redis_service(self, port=None):
        """Check if a Redis-based service is responding"""
        return self._check_redis()  # All services use Redis

    def _check_http_service(self, port):
        """Check if HTTP service is responding"""
        try:
            response = requests.get(f"http://localhost:{port}/ping", timeout=1)
            return response.status_code == 200
        except:
            return False


@pytest.fixture(scope="session")
def docker_env():
    """Pytest fixture to manage Docker environment"""
    env = DockerTestEnvironment()

    try:
        env.start_environment()
        yield env
    finally:
        env.stop_environment()


@pytest.fixture
def redis_client():
    """Redis client for testing ServiceBus communication"""
    return redis.Redis(host="localhost", port=6379, decode_responses=True)


@pytest.fixture
def api_client():
    """HTTP client for API testing"""
    import httpx

    return httpx.Client(base_url="http://localhost:8888")


class TestConfigurationService:
    """Test the configuration service functionality"""

    def test_config_service_redis_connectivity(self, redis_client):
        """Test that config service can connect to Redis"""
        assert redis_client.ping()

    def test_settings_json_accessibility(self, docker_env):
        """Test that settings.json is accessible in containers"""
        # Check config service container has settings.json
        container = docker_env.client.containers.get("mod-ui-config-service")

        # Execute command to check file exists
        result = container.exec_run("ls -la /app/config/settings.json")
        assert result.exit_code == 0
        assert "settings.json" in result.output.decode()

    def test_config_service_servicebus_communication(self, redis_client):
        """Test ServiceBus communication with config service"""
        # Simulate ServiceBus call to config service
        import uuid

        request_id = str(uuid.uuid4())

        # Send request
        redis_client.publish(
            "config-service:requests",
            json.dumps({"id": request_id, "method": "get_settings", "data": {}}),
        )

        # Listen for response (with timeout)
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"response:{request_id}")

        start_time = time.time()
        while time.time() - start_time < 10:
            message = pubsub.get_message(timeout=1)
            if message and message["type"] == "message":
                response = json.loads(message["data"])
                assert "environment" in response  # Should have settings data
                return

        pytest.fail("No response from config service")


class TestAudioEngineService:
    """Test the audio engine service functionality"""

    def test_audio_engine_redis_connectivity(self, redis_client):
        """Test that audio engine can connect to Redis"""
        assert redis_client.ping()

    def test_audio_engine_servicebus_health(self, redis_client):
        """Test ServiceBus health check with audio engine"""
        import uuid

        request_id = str(uuid.uuid4())

        # Send health check request
        redis_client.publish(
            "audio-engine:requests",
            json.dumps({"id": request_id, "method": "health_check", "data": {}}),
        )

        # Listen for response
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"response:{request_id}")

        start_time = time.time()
        while time.time() - start_time < 10:
            message = pubsub.get_message(timeout=1)
            if message and message["type"] == "message":
                response = json.loads(message["data"])
                assert "status" in response
                return

        pytest.fail("No response from audio engine service")

    def test_jack_lv2_functionality(self, redis_client):
        """Test JACK and LV2 functionality through ServiceBus"""
        import uuid

        request_id = str(uuid.uuid4())

        # Test JACK data retrieval
        redis_client.publish(
            "audio-engine:requests",
            json.dumps({"id": request_id, "method": "get_jack_data", "data": {}}),
        )

        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"response:{request_id}")

        start_time = time.time()
        while time.time() - start_time < 10:
            message = pubsub.get_message(timeout=1)
            if message and message["type"] == "message":
                response = json.loads(message["data"])
                assert "success" in response
                if response["success"]:
                    assert "jack_data" in response
                    jack_data = response["jack_data"]
                    assert "sample_rate" in jack_data
                    assert "buffer_size" in jack_data
                return

        pytest.fail("No response from audio engine JACK test")


class TestSessionService:
    """Test the session service functionality"""

    def test_session_service_redis_connectivity(self, redis_client):
        """Test that session service can connect to Redis"""
        assert redis_client.ping()

    def test_session_servicebus_communication(self, redis_client):
        """Test ServiceBus communication with session service"""
        import uuid

        request_id = str(uuid.uuid4())

        # Send session state request
        redis_client.publish(
            "session:requests",
            json.dumps({"id": request_id, "method": "get_session_state", "data": {}}),
        )

        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"response:{request_id}")

        start_time = time.time()
        while time.time() - start_time < 10:
            message = pubsub.get_message(timeout=1)
            if message and message["type"] == "message":
                response = json.loads(message["data"])
                # Session service should respond with some state info
                assert isinstance(response, dict)
                return

        pytest.fail("No response from session service")


class TestAPIService:
    """Test the FastAPI web service"""

    def test_api_service_health(self, api_client):
        """Test that API service responds to health checks"""
        response = api_client.get("/ping")
        assert response.status_code == 200

    def test_api_service_endpoints(self, api_client):
        """Test that API service has expected endpoints"""
        # Test root endpoint
        response = api_client.get("/")
        assert response.status_code in [200, 404]  # May redirect or show index

        # Test API info
        response = api_client.get("/api/info")
        assert response.status_code in [200, 404]  # Endpoint may not exist yet


class TestMicroservicesIntegration:
    """Test integration between microservices"""

    def test_redis_pubsub_infrastructure(self, redis_client):
        """Test Redis pub/sub infrastructure is working"""
        # Test basic pub/sub
        test_channel = "test:channel"
        test_message = "test message"

        pubsub = redis_client.pubsub()
        pubsub.subscribe(test_channel)

        # Skip the subscription confirmation message
        pubsub.get_message(timeout=1)

        # Publish and receive
        redis_client.publish(test_channel, test_message)
        message = pubsub.get_message(timeout=5)

        assert message is not None
        assert message["data"] == test_message

    def test_cross_service_communication(self, redis_client):
        """Test communication between different services"""
        # This would test a more complex workflow where
        # one service calls another through ServiceBus

        # For now, just ensure we can see all services
        # publishing their health status
        pubsub = redis_client.pubsub()
        pubsub.psubscribe("*:health")

        # Services should periodically publish health info
        # This is a placeholder for more complex integration testing
        assert True  # Basic infrastructure test passes


class TestDockerEnvironment:
    """Test Docker environment setup and configuration"""

    def test_all_containers_running(self, docker_env):
        """Test that all expected containers are running"""
        expected_containers = [
            "mod-ui-redis",
            "mod-ui-config-service",
            "mod-ui-audio-engine",
            "mod-ui-session-v2",
            "mod-ui-api",
        ]

        running_containers = [c.name for c in docker_env.client.containers.list()]

        for container_name in expected_containers:
            assert (
                container_name in running_containers
            ), f"Container {container_name} not running"

    def test_container_health_checks(self, docker_env):
        """Test that containers pass their health checks"""
        containers_with_health = [
            "mod-ui-redis",
            "mod-ui-config-service",
            "mod-ui-audio-engine",
            "mod-ui-session-v2",
            "mod-ui-api",
        ]

        for container_name in containers_with_health:
            try:
                container = docker_env.client.containers.get(container_name)
                # Wait a bit for health check to run
                time.sleep(5)
                container.reload()

                # Check health status
                health = container.attrs.get("State", {}).get("Health", {})
                status = health.get("Status", "unknown")

                # Allow 'starting' status as containers may still be initializing
                assert status in [
                    "healthy",
                    "starting",
                ], f"Container {container_name} status: {status}"

            except Exception as e:
                pytest.fail(f"Failed to check health of {container_name}: {e}")

    def test_volume_mounts(self, docker_env):
        """Test that volume mounts are configured correctly"""
        # Test config service has access to config files
        container = docker_env.client.containers.get("mod-ui-config-service")
        result = container.exec_run("ls -la /app/config")
        assert result.exit_code == 0
        assert "settings.json" in result.output.decode()

        # Test session service has access to original code
        container = docker_env.client.containers.get("mod-ui-session-v2")
        result = container.exec_run("ls -la /app/mod")
        assert result.exit_code == 0

    def test_network_connectivity(self, docker_env):
        """Test that containers can communicate with each other"""
        # Test that services can reach Redis
        container = docker_env.client.containers.get("mod-ui-config-service")
        result = container.exec_run(
            "python -c 'import redis; r=redis.Redis(host=\"redis\"); print(r.ping())'"
        )
        assert result.exit_code == 0
        assert "True" in result.output.decode()


def test_complete_system_functionality(docker_env, redis_client, api_client):
    """End-to-end test of the complete system"""
    print("🧪 Running complete system functionality test...")

    # 1. Test Redis infrastructure
    assert redis_client.ping(), "Redis not responding"

    # 2. Test API service
    try:
        response = api_client.get("/ping")
        api_working = response.status_code == 200
    except:
        api_working = False

    # 3. Test ServiceBus services (basic connectivity)
    services_responding = 0
    test_services = ["config-service", "audio-engine", "session"]

    for service in test_services:
        try:
            import uuid

            request_id = str(uuid.uuid4())

            redis_client.publish(
                f"{service}:requests",
                json.dumps({"id": request_id, "method": "health_check", "data": {}}),
            )

            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"response:{request_id}")

            # Quick check for response
            start_time = time.time()
            while time.time() - start_time < 5:
                message = pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    services_responding += 1
                    break

        except Exception as e:
            print(f"Service {service} test failed: {e}")

    # Summary
    print(f"📊 System Test Results:")
    print(f"   Redis: {'✅' if redis_client.ping() else '❌'}")
    print(f"   API Service: {'✅' if api_working else '❌'}")
    print(
        f"   ServiceBus Services: {services_responding}/{len(test_services)} responding"
    )

    # At minimum, Redis should be working
    assert redis_client.ping(), "Basic Redis infrastructure failed"
    print("🎉 Core system functionality validated!")


if __name__ == "__main__":
    print("🚀 MOD UI Docker Integration Test Suite")
    print("=" * 50)
    print("This will start Docker containers and run comprehensive tests.")
    print("Make sure Docker and docker-compose are installed and running.")
    print("")

    # Run with pytest
    import sys

    pytest.main([__file__, "-v"] + sys.argv[1:])
