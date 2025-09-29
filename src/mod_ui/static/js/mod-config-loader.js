/**
 * MOD UI Client Configuration Loader
 *
 * Replaces the template-based configuration system with API-based configuration loading.
 * This file loads all configuration data needed by the JavaScript client from the WebUI Gateway API.
 */

// Configuration loading state
window.MOD_CONFIG = {
  loaded: false,
  loading: false,
  data: {},
  error: null,
};

/**
 * Load client configuration from API
 * @returns {Promise<Object>} Configuration object
 */
async function loadClientConfig() {
  if (window.MOD_CONFIG.loaded) {
    return window.MOD_CONFIG.data;
  }

  if (window.MOD_CONFIG.loading) {
    // Wait for existing load to complete
    return new Promise((resolve, reject) => {
      const checkLoaded = () => {
        if (window.MOD_CONFIG.loaded) {
          resolve(window.MOD_CONFIG.data);
        } else if (window.MOD_CONFIG.error) {
          reject(window.MOD_CONFIG.error);
        } else {
          setTimeout(checkLoaded, 100);
        }
      };
      checkLoaded();
    });
  }

  window.MOD_CONFIG.loading = true;

  try {
    // Determine WebUI Gateway URL
    const gatewayHost = window.location.hostname;
    const gatewayPort = "8081"; // WebUI Gateway port
    const gatewayBaseUrl = `http://${gatewayHost}:${gatewayPort}/api`;

    console.log("Loading client configuration from:", gatewayBaseUrl);

    // Load main configuration
    const configResponse = await fetch(`${gatewayBaseUrl}/client/config`);
    if (!configResponse.ok) {
      throw new Error(
        `Failed to load configuration: ${configResponse.status} ${configResponse.statusText}`
      );
    }

    const config = await configResponse.json();

    // Store configuration
    window.MOD_CONFIG.data = config;
    window.MOD_CONFIG.loaded = true;
    window.MOD_CONFIG.loading = false;

    console.log("Client configuration loaded:", config);

    return config;
  } catch (error) {
    console.error("Failed to load client configuration:", error);
    window.MOD_CONFIG.error = error;
    window.MOD_CONFIG.loading = false;
    throw error;
  }
}

/**
 * Initialize global variables from configuration
 * Replaces the template-based variable initialization
 */
async function initializeGlobalVariables() {
  try {
    const config = await loadClientConfig();

    // Initialize global variables that were previously set through templates
    window.VERSION = config.version;
    window.SAMPLERATE = config.sampleRate;
    window.BUFFERSIZE = config.bufferSize;
    window.NOTIFICATIONS_ENABLED = config.notifications_enabled;
    window.HARDWARE_PROFILE = config.hardware_profile;
    window.DEFAULT_ICON_TEMPLATE = config.default_icon_template;
    window.DEFAULT_SETTINGS_TEMPLATE = config.default_settings_template;
    window.DEFAULT_PEDALBOARD = config.default_pedalboard;
    window.FAVORITES = config.favorites;
    window.PREFERENCES = config.preferences;
    window.ADDRESSING_PAGES = config.addressing_pages;
    window.DEBUG = config.debug;

    // Cloud service URLs
    window.CLOUD_URL = config.cloud_url;
    window.CLOUD_LABS_URL = config.cloud_labs_url;
    window.PLUGINS_URL = config.plugins_url;
    window.PEDALBOARDS_URL = config.pedalboards_url;
    window.PEDALBOARDS_LABS_URL = config.pedalboards_labs_url;
    window.CONTROLCHAIN_URL = config.controlchain_url;

    // Device type detection
    window.USING_MOD_DESKTOP = config.using_desktop;
    window.USING_MOD_DEVICE = config.using_mod && !config.using_desktop;

    // Derived variables
    window.CLOUD_TERMS_ACCEPTED =
      window.PREFERENCES &&
      window.PREFERENCES["cloud-terms-accepted"] === "true";

    // Session/pedalboard info
    window.BUNDLEPATH = config.bundlepath;
    window.TITLE = config.title;
    window.SIZE = config.size;
    window.FULLTITLE = config.fulltitle;
    window.TITLEBLEND = config.titleblend;

    // Hardware info
    window.BIN_COMPAT = config.bin_compat;
    window.CODEC_TRUEBYPASS = config.codec_truebypass;
    window.FACTORY_PEDALBOARDS = config.factory_pedalboards;
    window.PLATFORM = config.platform;
    window.LV2_PLUGIN_DIR = config.lv2_plugin_dir;

    // User info
    window.USER_NAME = config.user_name;
    window.USER_EMAIL = config.user_email;

    // Development configuration
    window.DEV_API_CLASS = config.dev_api_class;

    // Initialize INFO object
    window.INFO = {
      hardware: config.hardware_profile,
      version: config.version,
    };

    console.log("Global variables initialized from configuration");

    // Dispatch event to signal configuration is ready
    const event = new CustomEvent("mod-config-loaded", {
      detail: { config: config },
    });
    document.dispatchEvent(event);

    return config;
  } catch (error) {
    console.error("Failed to initialize global variables:", error);

    // Initialize with fallback values to prevent errors
    window.VERSION = Date.now().toString();
    window.SAMPLERATE = 48000;
    window.BUFFERSIZE = 256;
    window.NOTIFICATIONS_ENABLED = true;
    window.HARDWARE_PROFILE = {};
    window.DEFAULT_ICON_TEMPLATE = "";
    window.DEFAULT_SETTINGS_TEMPLATE = "";
    window.DEFAULT_PEDALBOARD = "";
    window.FAVORITES = [];
    window.PREFERENCES = {};
    window.ADDRESSING_PAGES = 0;
    window.DEBUG = true;
    window.CLOUD_URL = "https://cloud.moddevices.com";
    window.USING_MOD_DESKTOP = false;
    window.USING_MOD_DEVICE = false;
    window.CLOUD_TERMS_ACCEPTED = false;
    window.INFO = { hardware: {}, version: window.VERSION };

    throw error;
  }
}

/**
 * Load templates from API
 * @returns {Promise<Object>} Templates object
 */
async function loadTemplates() {
  try {
    const gatewayHost = window.location.hostname;
    const gatewayPort = "8081";
    const gatewayBaseUrl = `http://${gatewayHost}:${gatewayPort}/api`;

    const templatesResponse = await fetch(`${gatewayBaseUrl}/client/templates`);
    if (!templatesResponse.ok) {
      throw new Error(
        `Failed to load templates: ${templatesResponse.status} ${templatesResponse.statusText}`
      );
    }

    const templatesData = await templatesResponse.json();
    window.TEMPLATES = templatesData.templates;

    console.log("Templates loaded:", window.TEMPLATES);

    return window.TEMPLATES;
  } catch (error) {
    console.error("Failed to load templates:", error);
    window.TEMPLATES = {}; // Initialize empty templates to prevent errors
    throw error;
  }
}

/**
 * Update asset URLs with version parameter for cache busting
 */
function updateAssetVersions() {
  if (!window.VERSION) {
    console.warn("VERSION not available for cache busting");
    return;
  }

  // Update CSS files
  const cssLinks = document.querySelectorAll(
    'link[rel="stylesheet"][href*="?v={{version}}"]'
  );
  cssLinks.forEach((link) => {
    const href = link.getAttribute("href");
    if (href) {
      link.setAttribute(
        "href",
        href.replace("?v={{version}}", `?v=${window.VERSION}`)
      );
    }
  });

  // Update JavaScript files
  const jsScripts = document.querySelectorAll('script[src*="?v={{version}}"]');
  jsScripts.forEach((script) => {
    const src = script.getAttribute("src");
    if (src) {
      script.setAttribute(
        "src",
        src.replace("?v={{version}}", `?v=${window.VERSION}`)
      );
    }
  });

  console.log("Asset versions updated with version:", window.VERSION);
}

/**
 * Main initialization function
 * Call this when the page loads to initialize configuration
 */
async function initializeModUI() {
  try {
    console.log("Initializing MOD UI client configuration...");

    // Load configuration and initialize global variables
    await initializeGlobalVariables();

    // Load templates
    await loadTemplates();

    // Update asset versions for cache busting
    updateAssetVersions();

    console.log("MOD UI client configuration initialization complete");

    return true;
  } catch (error) {
    console.error("MOD UI initialization failed:", error);

    // Show user-friendly error message
    const errorDiv = document.createElement("div");
    errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff6b6b;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 10000;
            max-width: 500px;
            text-align: center;
        `;
    errorDiv.innerHTML = `
            <strong>Configuration Error</strong><br>
            Failed to load MOD UI configuration. Please check that the WebUI Gateway is running on port 8081.
            <br><br>
            <small>Error: ${error.message}</small>
        `;
    document.body.appendChild(errorDiv);

    // Auto-hide error after 10 seconds
    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.parentNode.removeChild(errorDiv);
      }
    }, 10000);

    return false;
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeModUI);
} else {
  // DOM already loaded
  initializeModUI();
}
