"""""""""

Unit Tests for Configuration Service

Unit Tests for Configuration ServiceUnit Tests for Configuration Service

Tests for the MOD UI Configuration Service endpoints and functionality.

"""



import jsonTests for the MOD UI Configuration Service endpoints and functionality.Tests for the MOD UI Configuration Service endpoints and functionality.

import pytest

from unittest.mock import patch, mock_open""""""



from fastapi.testclient import TestClient

from src.mod_ui.services.config_service.main import app

import jsonimport sys

# Create test client

client = TestClient(app)import pytestfrom pathlib import Path



class TestConfigService:from unittest.mock import patch, mock_openfrom unittest.mock import MagicMock, patch

    """Test cases for the Configuration Service"""



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_health_check(self, mock_path):from fastapi.testclient import TestClientimport pytest

        """Test the basic health check endpoint"""

        # Mock the settings file pathfrom src.mod_ui.services.config_service.main import app

        mock_path.exists.return_value = True

# Add the project root to Python path

        # Mock the file content

        mock_settings = {# Create test clientproject_root = Path(__file__).parent.parent.parent.parent.parent.parent

            "environment": {"dev_environment": False},

            "device": {"api_key": None}client = TestClient(app)sys.path.insert(0, str(project_root))

        }



        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/health")class TestConfigService:from fastapi.testclient import TestClient

            assert response.status_code == 200

            data = response.json()    """Test cases for the Configuration Service"""

            assert data["status"] == "healthy"

            assert data["service"] == "config-service"from src.mod_ui.services.config_service.main import app



    def test_config_overview(self):    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

        """Test the configuration overview endpoint"""

        response = client.get("/api/v1/config/")    def test_health_check(self, mock_path):# Create test client

        assert response.status_code == 200

        data = response.json()        """Test the basic health check endpoint"""client = TestClient(app)

        assert "endpoints" in data

        assert "description" in data        # Mock the settings file path

        assert "/api/v1/config/settings" in data["endpoints"]

        assert "/api/v1/config/settings/{section}" in data["endpoints"]        mock_path.exists.return_value = True

        assert "/api/v1/config/settings/{section}/{key}" in data["endpoints"]

class TestConfigService:

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_all_settings_success(self, mock_path):        # Mock the file content    """Test cases for the Configuration Service"""

        """Test retrieving all settings successfully"""

        mock_path.exists.return_value = True        mock_settings = {



        mock_settings = {            "environment": {"dev_environment": False},    def test_health_check(self):

            "environment": {

                "dev_environment": True,            "device": {"api_key": None}        """Test the basic health check endpoint"""

                "log_level": 2

            },        }        response = client.get("/health")

            "device": {

                "api_key": "test_key",        assert response.status_code == 200

                "device_uid": "test_uid"

            }        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):        data = response.json()

        }

            response = client.get("/health")        assert data["status"] == "healthy"

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings")            assert response.status_code == 200        assert data["service"] == "config-service"

            assert response.status_code == 200

            data = response.json()            data = response.json()

            assert data["environment"]["dev_environment"] is True

            assert data["environment"]["log_level"] == 2            assert data["status"] == "healthy"    def test_config_overview(self):

            assert data["device"]["api_key"] == "test_key"

            assert data["service"] == "config-service"        """Test the configuration overview endpoint"""

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_all_settings_file_not_found(self, mock_path):        response = client.get("/api/v1/config/")

        """Test retrieving all settings when file doesn't exist"""

        mock_path.exists.return_value = False    def test_config_overview(self):        assert response.status_code == 200



        response = client.get("/api/v1/config/settings")        """Test the configuration overview endpoint"""        data = response.json()

        assert response.status_code == 500

        data = response.json()        response = client.get("/api/v1/config/")        assert "endpoints" in data

        assert "Failed to retrieve settings" in data["detail"]

        assert response.status_code == 200        assert "description" in data

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_settings_section_success(self, mock_path):        data = response.json()        assert "/api/v1/config/settings" in data["endpoints"]

        """Test retrieving a specific settings section"""

        mock_path.exists.return_value = True        assert "endpoints" in data



        mock_settings = {        assert "description" in data    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

            "environment": {"dev_environment": True},

            "device": {"api_key": "test_key"}        assert "/api/v1/config/settings" in data["endpoints"]    def test_get_all_settings_success(self, mock_settings):

        }

        assert "/api/v1/config/settings/{section}" in data["endpoints"]        """Test retrieving all settings successfully"""

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings/environment")        assert "/api/v1/config/settings/{section}/{key}" in data["endpoints"]        # Mock the settings module

            assert response.status_code == 200

            data = response.json()        mock_settings.__name__ = "mod.settings"

            assert data["dev_environment"] is True

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        mock_settings.TEST_STRING = "test_value"

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_settings_section_not_found(self, mock_path):    def test_get_all_settings_success(self, mock_path):        mock_settings.TEST_INT = 42

        """Test retrieving a non-existent settings section"""

        mock_path.exists.return_value = True        """Test retrieving all settings successfully"""        mock_settings.TEST_BOOL = True



        mock_settings = {"environment": {"dev_environment": True}}        mock_path.exists.return_value = True        mock_settings.TEST_LIST = [1, 2, 3]



        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings/nonexistent")

            assert response.status_code == 404        mock_settings = {        # Mock dir() to return our test attributes

            data = response.json()

            assert "not found" in data["detail"]            "environment": {        with patch("src.mod_ui.services.config_service.routers.config.dir") as mock_dir:



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')                "dev_environment": True,            mock_dir.return_value = [

    def test_get_setting_by_key_success(self, mock_path):

        """Test retrieving a specific setting by section and key"""                "log_level": 2                "TEST_STRING",

        mock_path.exists.return_value = True

            },                "TEST_INT",

        mock_settings = {

            "environment": {"dev_environment": True, "log_level": 2}            "device": {                "TEST_BOOL",

        }

                "api_key": "test_key",                "TEST_LIST",

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings/environment/log_level")                "device_uid": "test_uid"            ]

            assert response.status_code == 200

            assert response.json() == 2            }



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        }            response = client.get("/api/v1/config/settings")

    def test_get_setting_by_key_section_not_found(self, mock_path):

        """Test retrieving a setting from non-existent section"""            assert response.status_code == 200

        mock_path.exists.return_value = True

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):            data = response.json()

        mock_settings = {"environment": {"dev_environment": True}}

            response = client.get("/api/v1/config/settings")

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings/nonexistent/key")            assert response.status_code == 200            assert data["TEST_STRING"] == "test_value"

            assert response.status_code == 404

            data = response.json()            data = response.json()            assert data["TEST_INT"] == 42

            assert "section" in data["detail"] and "not found" in data["detail"]

            assert data["environment"]["dev_environment"] is True            assert data["TEST_BOOL"] is True

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_setting_by_key_not_found(self, mock_path):            assert data["environment"]["log_level"] == 2            assert data["TEST_LIST"] == [1, 2, 3]

        """Test retrieving a non-existent setting from valid section"""

        mock_path.exists.return_value = True            assert data["device"]["api_key"] == "test_key"



        mock_settings = {"environment": {"dev_environment": True}}    @patch("src.mod_ui.services.config_service.routers.config.settings_module")



        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')    def test_get_all_settings_module_none(self, mock_settings):

            response = client.get("/api/v1/config/settings/environment/nonexistent")

            assert response.status_code == 404    def test_get_all_settings_file_not_found(self, mock_path):        """Test retrieving all settings when module fails to load"""

            data = response.json()

            assert "not found in section" in data["detail"]        """Test retrieving all settings when file doesn't exist"""        # Mock settings_module as None



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        mock_path.exists.return_value = False        with patch(

    def test_config_health_check_healthy(self, mock_path):

        """Test the config-specific health check when settings are loaded"""            "src.mod_ui.services.config_service.routers.config.settings_module", None

        mock_path.exists.return_value = True

        response = client.get("/api/v1/config/settings")        ):

        mock_settings = {"environment": {"dev_environment": False}}

        assert response.status_code == 500            response = client.get("/api/v1/config/settings")

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            # First load the settings        data = response.json()            assert response.status_code == 500

            client.get("/api/v1/config/settings")

        assert "Failed to retrieve settings" in data["detail"]            data = response.json()

            # Then check health

            response = client.get("/api/v1/config/health")            assert "Failed to load settings module" in data["detail"]

            assert response.status_code == 200

            data = response.json()    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

            assert data["status"] == "healthy"

            assert data["service"] == "config-service"    def test_get_settings_section_success(self, mock_path):    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

            assert data["settings_loaded"] is True

        """Test retrieving a specific settings section"""    def test_get_setting_by_key_success(self, mock_settings):

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_config_health_check_unhealthy(self, mock_path):        mock_path.exists.return_value = True        """Test retrieving a specific setting by key"""

        """Test the config health check when settings fail to load"""

        mock_path.exists.return_value = False        mock_settings.TEST_SETTING = "test_value"



        response = client.get("/api/v1/config/health")        mock_settings = {

        assert response.status_code == 200

        data = response.json()            "environment": {"dev_environment": True},        response = client.get("/api/v1/config/settings/TEST_SETTING")

        assert data["status"] == "unhealthy"

        assert data["service"] == "config-service"            "device": {"api_key": "test_key"}        assert response.status_code == 200

        assert data["settings_loaded"] is False

        assert "error" in data        }        assert response.json() == "test_value"



if __name__ == "__main__":

    pytest.main([__file__, "-v"])
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

            response = client.get("/api/v1/config/settings/environment")    def test_get_setting_by_key_not_found(self, mock_settings):

            assert response.status_code == 200        """Test retrieving a non-existent setting"""

            data = response.json()        # Mock hasattr to return False

            assert data["dev_environment"] is True        with patch(

            "src.mod_ui.services.config_service.routers.config.hasattr"

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        ) as mock_hasattr:

    def test_get_settings_section_not_found(self, mock_path):            mock_hasattr.return_value = False

        """Test retrieving a non-existent settings section"""

        mock_path.exists.return_value = True            response = client.get("/api/v1/config/settings/NON_EXISTENT")

            assert response.status_code == 404

        mock_settings = {"environment": {"dev_environment": True}}            data = response.json()

            assert "not found" in data["detail"]

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            response = client.get("/api/v1/config/settings/nonexistent")    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

            assert response.status_code == 404    def test_get_setting_by_key_module_none(self, mock_settings):

            data = response.json()        """Test retrieving a setting when module fails to load"""

            assert "not found" in data["detail"]        with patch(

            "src.mod_ui.services.config_service.routers.config.settings_module", None

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        ):

    def test_get_setting_by_key_success(self, mock_path):            response = client.get("/api/v1/config/settings/TEST_SETTING")

        """Test retrieving a specific setting by section and key"""            assert response.status_code == 500

        mock_path.exists.return_value = True            data = response.json()

            assert "Failed to load settings module" in data["detail"]

        mock_settings = {

            "environment": {"dev_environment": True, "log_level": 2}    def test_config_health_check(self):

        }        """Test the config-specific health check"""

        response = client.get("/api/v1/config/health")

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):        assert response.status_code == 200

            response = client.get("/api/v1/config/settings/environment/log_level")        data = response.json()

            assert response.status_code == 200        assert data["status"] == "healthy"

            assert response.json() == 2        assert data["service"] == "config-service"

        assert "settings_loaded" in data

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')

    def test_get_setting_by_key_section_not_found(self, mock_path):    @patch("src.mod_ui.services.config_service.routers.config.settings_module", None)

        """Test retrieving a setting from non-existent section"""    def test_config_health_check_unhealthy(self):

        mock_path.exists.return_value = True        """Test the config health check when settings module fails to load"""

        response = client.get("/api/v1/config/health")

        mock_settings = {"environment": {"dev_environment": True}}        assert response.status_code == 200

        data = response.json()

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):        assert data["status"] == "unhealthy"

            response = client.get("/api/v1/config/settings/nonexistent/key")        assert data["service"] == "config-service"

            assert response.status_code == 404        assert data["settings_loaded"] is False

            data = response.json()        assert "error" in data

            assert "section" in data["detail"] and "not found" in data["detail"]



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')class TestSettingsSerialization:

    def test_get_setting_by_key_not_found(self, mock_path):    """Test cases for settings serialization"""

        """Test retrieving a non-existent setting from valid section"""

        mock_path.exists.return_value = True    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

    def test_serialize_complex_object(self, mock_settings):

        mock_settings = {"environment": {"dev_environment": True}}        """Test serialization of complex objects"""



        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):        class TestClass:

            response = client.get("/api/v1/config/settings/environment/nonexistent")            def __init__(self):

            assert response.status_code == 404                self.value = 42

            data = response.json()

            assert "not found in section" in data["detail"]        mock_settings.COMPLEX_OBJ = TestClass()



    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')        with patch("src.mod_ui.services.config_service.routers.config.dir") as mock_dir:

    def test_config_health_check_healthy(self, mock_path):            mock_dir.return_value = ["COMPLEX_OBJ"]

        """Test the config-specific health check when settings are loaded"""

        mock_path.exists.return_value = True            response = client.get("/api/v1/config/settings")

            assert response.status_code == 200

        mock_settings = {"environment": {"dev_environment": False}}            data = response.json()

            assert data["COMPLEX_OBJ"] == {"value": 42}

        with patch('builtins.open', mock_open(read_data=json.dumps(mock_settings))):

            # First load the settings    @patch("src.mod_ui.services.config_service.routers.config.settings_module")

            client.get("/api/v1/config/settings")    def test_serialize_unserializable_object(self, mock_settings):

        """Test serialization of unserializable objects"""

            # Then check health        # Create an object that can't be serialized normally

            response = client.get("/api/v1/config/health")        mock_settings.UNSERIALIZABLE = lambda x: x

            assert response.status_code == 200

            data = response.json()        with patch("src.mod_ui.services.config_service.routers.config.dir") as mock_dir:

            assert data["status"] == "healthy"            mock_dir.return_value = ["UNSERIALIZABLE"]

            assert data["service"] == "config-service"

            assert data["settings_loaded"] is True            response = client.get("/api/v1/config/settings")

            assert response.status_code == 200

    @patch('src.mod_ui.services.config_service.routers.config.SETTINGS_JSON_PATH')            data = response.json()

    def test_config_health_check_unhealthy(self, mock_path):            assert "<callable:" in data["UNSERIALIZABLE"]

        """Test the config health check when settings fail to load"""

        mock_path.exists.return_value = False

if __name__ == "__main__":

        response = client.get("/api/v1/config/health")    pytest.main([__file__, "-v"])

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "config-service"
        assert data["settings_loaded"] is False
        assert "error" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])