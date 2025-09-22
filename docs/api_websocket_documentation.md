# MOD UI API and WebSocket Documentation

This document outlines the HTTP API endpoints and WebSocket methods used by the MOD UI frontend, as well as backend APIs that are not used by the frontend.

## APIs Used by the Frontend

These are the API endpoints and WebSocket messages actively used by the JavaScript files in the `html/js` directory.

### HTTP API Calls

| Method | Endpoint                               | Description                                       |
|--------|----------------------------------------|---------------------------------------------------|
| GET    | `/effect/list`                         | Get all available plugins.                        |
| GET    | `/effect/get`                          | Get detailed information for a specific plugin.   |
| POST   | `/effect/install`                      | Install a new plugin.                             |
| GET    | `/effect/add/{instance}`               | Add a plugin instance to the pedalboard.          |
| GET    | `/effect/remove/{instance}`            | Remove a plugin instance from the pedalboard.     |
| GET    | `/effect/connect/{from}/{to}`          | Connect two plugin ports.                         |
| GET    | `/effect/disconnect/{from}/{to}`       | Disconnect two plugin ports.                      |
| POST   | `/effect/preset/load/{instance}`       | Load a preset for a plugin instance.              |
| GET    | `/effect/preset/save_new/{instance}`   | Save a new preset for a plugin instance.          |
| GET    | `/effect/preset/save_replace/{instance}`| Replace an existing preset.                       |
| GET    | `/effect/preset/delete/{instance}`     | Delete a preset.                                  |
| POST   | `/favorites/add`                       | Add a plugin to the user's favorites.             |
| POST   | `/favorites/remove`                    | Remove a plugin from the user's favorites.        |
| GET    | `/snapshot/name`                       | Get the name of a specific snapshot.              |
| POST   | `/snapshot/save`                       | Save the current state as a snapshot.             |
| GET    | `/snapshot/saveas`                     | Save the current state as a new snapshot.         |
| GET    | `/snapshot/rename`                     | Rename a snapshot.                                |
| GET    | `/snapshot/remove`                     | Remove a snapshot.                                |
| GET    | `/snapshot/list`                       | Get a list of all snapshots.                      |
| GET    | `/snapshot/load`                       | Load a specific snapshot.                         |
| POST   | `/pedalboard/save`                     | Save the current pedalboard.                      |
| POST   | `/pedalboard/load_bundle`              | Load a pedalboard from a bundle.                  |
| GET    | `/pedalboard/remove`                   | Remove a pedalboard.                              |
| GET    | `/pedalboard/info`                     | Get information about a pedalboard.               |
| GET    | `/pedalboard/factory_copy`             | Create a user copy of a factory pedalboard.       |
| GET    | `/bank/load`                           | Load all pedalboard banks.                        |
| POST   | `/bank/save`                           | Save the pedalboard banks.                        |
| GET    | `/system/info`                         | Get system hardware and software information.     |
| GET    | `/system/preferences`                  | Get system preferences.                           |
| POST   | `/system/exe`                          | Execute a system-level command (e.g., reboot).    |
| POST   | `/system/cleanup`                      | Clean up user data (banks, favorites, etc.).      |
| POST   | `/update/download`                     | Download a system update file.                    |
| POST   | `/update/begin`                        | Begin the system update process.                  |
| POST   | `/cc/download`                         | Download a Control Chain firmware update.         |
| POST   | `/cc/cancel`                         | Cancel a Control Chain firmware update.           |
| GET    | `/ping`                                | Ping the server to check for liveness.            |
| GET    | `/hello`                               | Check if the WebSocket server is online.          |
| GET    | `/truebypass/{channel}/{state}`        | Set the true bypass state for an audio channel.   |
| POST   | `/buffersize/{size}`                   | Set the JACK buffer size.                         |
| POST   | `/xruns/reset`                         | Reset the x-run counter.                          |
| POST   | `/cpu/freq/switch`                     | Switch the CPU frequency.                         |
| POST   | `/config/save`                         | Save a single configuration value.                |
| POST   | `/user/save`                           | Save the user's ID (name and email).              |
| GET    | `/lv2/bundles/{bundleId}`              | Get bundle information from the cloud.            |
| GET    | `/lv2/plugins`                         | Get plugin information from the cloud.            |

### WebSocket Messages

| Command                         | Payload                               | Description                                             |
|---------------------------------|---------------------------------------|---------------------------------------------------------|
| `data_ready`                    | `{counter}`                           | Sent in response to the server's `data_ready` message.  |
| `pong`                          |                                       | Sent in response to the server's `ping` message.        |
| `param_set`                     | `{port} {value}`                      | Set the value of a plugin parameter.                    |
| `patch_get`                     | `{instance} {uri}`                    | Get a patch property from a plugin.                     |
| `patch_set`                     | `{instance} {uri} {type} {value}`     | Set a patch property on a plugin.                       |
| `plugin_pos`                    | `{instance} {x} {y}`                  | Set the position of a plugin on the pedalboard canvas.  |
| `pb_size`                       | `{width} {height}`                    | Set the size of the pedalboard canvas.                  |
| `transport-rolling`             | `{0 or 1}`                            | Set the transport rolling state (play/stop).            |
| `transport-bpb`                 | `{value}`                             | Set the transport beats per bar.                        |
| `transport-bpm`                 | `{value}`                             | Set the transport beats per minute.                     |
| `show_external_ui`              | `{instance}`                          | Request to show the external GUI for a plugin.          |
| `link_enable`                   |                                       | Enable Ableton Link.                                    |
| `midi_clock_slave_enable`       |                                       | Enable MIDI clock slave mode.                           |
| `set_internal_transport_source` |                                       | Set the transport source to internal.                   |

## APIs Present in `webserver.py` but Not Used by Frontend

These API endpoints are defined in `mod/webserver.py` but do not appear to be used by the frontend JavaScript code. They might be used by other tools, for debugging, or are legacy endpoints.

| Method | Endpoint                                    | Description                                                              |
|--------|---------------------------------------------|--------------------------------------------------------------------------|
| GET    | `/effect/get_non_cached`                    | Get non-cached information for a specific plugin.                        |
| POST   | `/effect/parameter/address/{port}`          | Address a parameter to a hardware control.                               |
| POST   | `/effect/parameter/set`                     | Set a parameter value (alternative to WebSocket).                        |
| GET    | `/sdk/effect/install`                       | Install an effect from the SDK.                                          |
| POST   | `/sdk/effect/update`                        | Update an effect from the SDK.                                           |
| GET    | `/effect/resource/{path}`                   | Get a resource file for a plugin.                                        |
| GET    | `/effect/image/{image}`                     | Get an image file (thumbnail, screenshot) for a plugin.                  |
| GET    | `/effect/file/{prop}`                       | Get a file (stylesheet, javascript, etc.) for a plugin.                  |
| POST   | `/package/uninstall`                        | Uninstall a package (bundle) of plugins.                                 |
| GET    | `/pedalboard/list`                          | Get a list of all pedalboards.                                           |
| GET    | `/pedalboard/pack_bundle`                   | Pack a pedalboard into a downloadable bundle.                            |
| POST   | `/pedalboard/load_remote/{pedalboard_id}`   | Load a remote pedalboard.                                                |
| POST   | `/pedalboard/load_web`                      | Load a pedalboard from a web upload.                                     |
| GET    | `/pedalboard/image/{image}`                 | Get an image for a pedalboard.                                           |
| GET    | `/pedalboard/image/generate`                | Generate a new image for a pedalboard.                                   |
| GET    | `/pedalboard/image/check`                   | Check the status of a pedalboard image generation.                       |
| GET    | `/pedalboard/image/wait`                    | Wait for a pedalboard image generation to complete.                      |
| POST   | `/pedalboard/cv_addressing/plugin_port/add` | Add a CV addressing port to a plugin.                                    |
| POST   | `/pedalboard/cv_addressing/plugin_port/remove`| Remove a CV addressing port from a plugin.                             |
| POST   | `/pedalboard/transport/set_sync_mode/{mode}`| Set the transport sync mode.                                             |
| GET    | `/dashboard/clean`                          | Clear the dashboard (reset the current pedalboard).                      |
| GET    | `/{path}` (TemplateHandler)                 | Serves the main HTML pages and templates.                                |
| GET    | `/include/{path}` (TemplateLoader)          | Loads individual template files.                                         |
| GET    | `/templates.js` (BulkTemplateLoader)        | Loads all templates in bulk.                                             |
| WS     | `/remote-pb` (RemotePedalboardWebSocket)    | WebSocket for loading remote pedalboards.                                |
| WS     | `/remote-plugin` (RemotePluginWebSocket)    | WebSocket for installing remote plugins.                                 |
