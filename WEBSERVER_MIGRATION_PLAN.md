# Webserver Migration Plan

## Overview
Migrate all functionality from the Tornado-based `mod/webserver.py` to the new FastAPI architecture with Redis pub/sub communication.

## Analysis Summary
The webserver.py contains 86 HTTP routes, 3 WebSocket handlers, and numerous utility functions. The handlers are organized into several logical groups:

### Handler Categories

#### 1. System Management (4 endpoints)
- `/system/info` - SystemInfo - System information (hardware, software versions)
- `/system/prefs` - SystemPreferences - System preferences management
- `/system/exechange` - SystemExeChange - System executable changes
- `/system/cleanup` - SystemCleanup - System cleanup operations

#### 2. Update/Control Chain (4 endpoints)
- `/update/download/` - UpdateDownload - System update downloads
- `/update/begin` - UpdateBegin - Begin system update
- `/controlchain/download/` - ControlChainDownload - Control chain firmware
- `/controlchain/cancel/` - ControlChainCancel - Cancel control chain operations

#### 3. Effects Management (14 endpoints)
- `/effect/add/*` - EffectAdd - Add plugin to pedalboard
- `/effect/remove/*` - EffectRemove - Remove plugin from pedalboard
- `/effect/get` - EffectGet - Get plugin information (cached)
- `/effect/get_non_cached` - EffectGetNonCached - Get plugin info (non-cached)
- `/effect/bulk/?` - EffectBulk - Bulk effect operations
- `/effect/list` - EffectList - List all available plugins
- `/effect/parameter/address/*` - EffectParameterAddress - Parameter addressing
- `/effect/parameter/set/?` - EffectParameterSet - Set parameter values
- `/effect/preset/load/*` - EffectPresetLoad - Load effect presets
- `/effect/preset/save_new/*` - EffectPresetSaveNew - Save new presets
- `/effect/preset/save_replace/*` - EffectPresetSaveReplace - Replace existing presets
- `/effect/preset/delete/*` - EffectPresetDelete - Delete presets
- `/effect/connect/*` - EffectConnect - Connect effect ports
- `/effect/disconnect/*` - EffectDisconnect - Disconnect effect ports

#### 4. Resources & Files (3 endpoints)
- `/resources/(.*)` - EffectResource - Static effect resources
- `/effect/image/(screenshot|thumbnail).png` - EffectImage - Effect images
- `/effect/file/(.*)` - EffectFile - Effect-related files

#### 5. Package Management (1 endpoint)
- `/package/uninstall` - PackageUninstall - Uninstall packages

#### 6. Pedalboard Management (16 endpoints)
- `/pedalboard/list` - PedalboardList - List saved pedalboards
- `/pedalboard/save` - PedalboardSave - Save current pedalboard
- `/pedalboard/pack_bundle/?` - PedalboardPackBundle - Pack pedalboard as bundle
- `/pedalboard/load_bundle/` - PedalboardLoadBundle - Load pedalboard bundle
- `/pedalboard/load_remote/*` - PedalboardLoadRemote - Load remote pedalboard
- `/pedalboard/load_web/` - PedalboardLoadWeb - Load web pedalboard
- `/pedalboard/factorycopy/` - PedalboardFactoryCopy - Copy factory pedalboard
- `/pedalboard/info/` - PedalboardInfo - Get pedalboard info
- `/pedalboard/remove/` - PedalboardRemove - Remove pedalboard
- `/pedalboard/image/(screenshot|thumbnail).png` - PedalboardImage - Pedalboard images
- `/pedalboard/image/generate` - PedalboardImageGenerate - Generate images
- `/pedalboard/image/check` - PedalboardImageCheck - Check image status
- `/pedalboard/image/wait` - PedalboardImageWait - Wait for image generation
- `/pedalboard/cv_addressing_plugin_port/add` - PedalboardCvAddressingPluginPortAdd
- `/pedalboard/cv_addressing_plugin_port/remove` - PedalboardCvAddressingPluginPortRemove
- `/pedalboard/transport/set_sync_mode/*` - PedalboardTransportSetSyncMode

#### 7. Snapshot Management (7 endpoints)
- `/snapshot/save` - SnapshotSave - Save snapshot
- `/snapshot/saveas` - SnapshotSaveAs - Save snapshot as
- `/snapshot/rename` - SnapshotRename - Rename snapshot
- `/snapshot/remove` - SnapshotRemove - Remove snapshot
- `/snapshot/list` - SnapshotList - List snapshots
- `/snapshot/name` - SnapshotName - Get snapshot name
- `/snapshot/load` - SnapshotLoad - Load snapshot

#### 8. Bank Management (2 endpoints)
- `/banks/?` - BankLoad - Load bank
- `/banks/save/?` - BankSave - Save bank

#### 9. Authentication (2 endpoints)
- `/auth/nonce/?$` - AuthNonce - Get authentication nonce
- `/auth/token/?$` - AuthToken - Exchange token

#### 10. Recording (5 endpoints)
- `/recording/start` - RecordingStart - Start recording
- `/recording/stop` - RecordingStop - Stop recording
- `/recording/play/(start|wait|stop)` - RecordingPlay - Recording playback
- `/recording/download` - RecordingDownload - Download recording
- `/recording/reset` - RecordingReset - Reset recording

#### 11. Tokens Management (3 endpoints)
- `/tokens/delete` - TokensDelete - Delete tokens
- `/tokens/get` - TokensGet - Get tokens
- `/tokens/save/?` - TokensSave - Save tokens

#### 12. File Management (1 endpoint)
- `/files/list/?` - FilesList - List files

#### 13. System Controls (9 endpoints)
- `/reset/?` - DashboardClean - Reset dashboard
- `/sdk/install/?` - SDKEffectInstaller - Install SDK effects
- `/sdk/update` - SDKEffectUpdater - Update SDK effects
- `/jack/get_midi_devices` - JackGetMidiDevices - Get MIDI devices
- `/jack/set_midi_devices` - JackSetMidiDevices - Set MIDI devices
- `/favorites/add` - FavoritesAdd - Add to favorites
- `/favorites/remove` - FavoritesRemove - Remove from favorites
- `/config/set` - SaveSingleConfigValue - Save config value
- `/ping/?` - Ping - Health check

#### 14. Hardware Controls (6 endpoints)
- `/hello/?` - Hello - Hello endpoint
- `/truebypass/(Left|Right)/(true|false)` - TrueBypass - True bypass control
- `/set_buffersize/(128|256)` - SetBufferSize - Set buffer size
- `/reset_xruns/` - ResetXruns - Reset audio dropouts
- `/switch_cpu_freq/` - SwitchCpuFreq - Switch CPU frequency
- `/save_user_id/` - SaveUserId - Save user ID

#### 15. Templates & Static Files (6 endpoints)
- `/(index.html)?$` - TemplateHandler - Main page template
- `/([a-z]+\.html)$` - TemplateHandler - HTML templates
- `/(allguis|sdk|settings)$` - TemplateHandler - Special pages
- `/load_template/([a-z_]+\.html)$` - TemplateLoader - Load templates
- `/js/templates.js$` - BulkTemplateLoader - Load JS templates
- `/(.*)`- TimelessStaticFileHandler - Static files

#### 16. WebSocket Handlers (3 endpoints)
- `/websocket/?$` - ServerWebSocket - Main WebSocket connection
- `/rpbsocket/?$` - RemotePedalboardWebSocket - Remote pedalboard WS
- `/rplsocket/?$` - RemotePluginWebSocket - Remote plugin WS

## Migration Strategy

### Phase 1: Core API Services (High Priority)
Create backend services for core functionality that needs Redis pub/sub communication:
1. **Effects Service** - Plugin management, parameter control, connections
2. **Pedalboard Service** - Pedalboard CRUD, loading, saving
3. **System Service** - System info, preferences, controls
4. **Snapshot Service** - Snapshot management
5. **Bank Service** - Bank management

### Phase 2: WebUI Gateway Routers (High Priority)
Create FastAPI routers in WebUI Gateway to replace HTTP endpoints:
1. **System Router** (`/api/system/*`)
2. **Effects Router** (`/api/effects/*`)  
3. **Pedalboard Router** (`/api/pedalboard/*`)
4. **Snapshot Router** (`/api/snapshots/*`)
5. **Bank Router** (`/api/banks/*`)

### Phase 3: File & Resource Handling (Medium Priority)
1. **Static File Service** - Handle static resources, effect files, images
2. **Upload Service** - Handle file uploads (bundles, packages)
3. **Template Service** - Dynamic template generation

### Phase 4: Real-time Communication (Medium Priority)
1. **WebSocket Service** - Replace Tornado WebSocket handlers
2. **Recording Service** - Audio recording functionality
3. **Authentication Service** - Token and session management

### Phase 5: Hardware Integration (Lower Priority)
Keep hardware-specific endpoints that require direct system access:
1. JACK configuration
2. True bypass controls
3. CPU frequency controls
4. Hardware-specific features

## Implementation Plan

### Step 1: Create Backend Services
```
src/mod_ui/services/
├── effects_service/
│   ├── main.py
│   ├── models.py
│   └── handlers.py
├── pedalboard_service/
│   ├── main.py
│   ├── models.py
│   └── handlers.py
├── system_service/
│   ├── main.py
│   ├── models.py
│   └── handlers.py
└── snapshot_service/
    ├── main.py
    ├── models.py
    └── handlers.py
```

### Step 2: Create FastAPI Routers
```
src/mod_ui/services/webui_gateway/routers/
├── system.py      # System management endpoints
├── effects.py     # Effect management endpoints
├── pedalboard.py  # Pedalboard management endpoints
├── snapshots.py   # Snapshot management endpoints
├── banks.py       # Bank management endpoints
├── files.py       # File management endpoints
├── recording.py   # Recording endpoints
└── auth.py        # Authentication endpoints
```

### Step 3: Update Docker Configuration
Add new services to docker-compose.dev.yml and configure networking.

### Step 4: Migrate WebSocket Functionality
Convert WebSocket handlers to FastAPI WebSocket endpoints with Redis pub/sub messaging.

## Migration Priority Order

### Immediate (Week 1)
1. Effects Service + Effects Router (most used functionality)
2. System Service + System Router (system info, health checks)

### Short-term (Week 2)
3. Pedalboard Service + Pedalboard Router
4. Snapshot Service + Snapshot Router

### Medium-term (Weeks 3-4)
5. Static file handling and resource management
6. Authentication and token management
7. Recording functionality

### Long-term (Weeks 5+)
8. WebSocket migration
9. Advanced features and optimizations
10. Full backward compatibility testing

## Compatibility Strategy

### API Compatibility
- Maintain exact same endpoint URLs
- Keep same request/response formats
- Preserve query parameter handling
- Maintain error response formats

### Session Integration
- Integrate with existing SESSION global object
- Maintain compatibility with session.py
- Preserve WebSocket message protocols

### Static File Serving
- Keep same static file URLs
- Maintain template system compatibility
- Preserve resource serving behavior

## Success Criteria
1. All existing frontend functionality works unchanged
2. No breaking changes to API contracts
3. Improved performance with Redis pub/sub
4. Clean separation of concerns
5. Scalable microservice architecture
6. Proper error handling and logging
7. Complete test coverage