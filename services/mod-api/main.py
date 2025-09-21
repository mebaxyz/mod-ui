#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from random import randint
from typing import Optional

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

# Import existing modules
from mod.session import SESSION
from mod.settings import (
    DESKTOP, LOG, DEV_API,
    HTML_DIR, DOWNLOAD_TMP_DIR, DEVICE_KEY, DEVICE_WEBSERVER_PORT,
    CLOUD_HTTP_ADDRESS, CLOUD_LABS_HTTP_ADDRESS,
    PLUGINS_HTTP_ADDRESS, PEDALBOARDS_HTTP_ADDRESS, CONTROLCHAIN_HTTP_ADDRESS,
    USER_BANKS_JSON_FILE,
    LV2_PLUGIN_DIR, LV2_PEDALBOARDS_DIR, IMAGE_VERSION,
    UPDATE_CC_FIRMWARE_FILE, UPDATE_MOD_OS_FILE, UPDATE_MOD_OS_HERLPER_FILE, USING_256_FRAMES_FILE,
    DEFAULT_ICON_TEMPLATE, DEFAULT_SETTINGS_TEMPLATE, DEFAULT_ICON_IMAGE,
    DEFAULT_PEDALBOARD, DEFAULT_SNAPSHOT_NAME, DATA_DIR, KEYS_PATH, USER_FILES_DIR,
    FAVORITES_JSON_FILE, PREFERENCES_JSON_FILE, USER_ID_JSON_FILE,
    DEV_HOST, UNTITLED_PEDALBOARD_NAME, MODEL_CPU, MODEL_TYPE, PEDALBOARDS_LABS_HTTP_ADDRESS)

from mod import (
    TextFileFlusher, WINDOWS,
    check_environment, jsoncall, safe_json_load,
    get_hardware_descriptor, get_unique_name, os_sync, symbolify,
)
from mod.bank import list_banks, save_banks, remove_pedalboard_from_banks
from modtools.utils import (
    kPedalboardInfoUserOnly, kPedalboardInfoFactoryOnly, kPedalboardInfoBoth,
    init as lv2_init, cleanup as lv2_cleanup,
    get_plugin_list, get_all_plugins, get_plugin_info, get_non_cached_plugin_info,
    get_plugin_gui, get_plugin_gui_mini,
    get_all_pedalboards, get_all_user_pedalboard_names, get_broken_pedalboards, get_pedalboard_info,
    get_jack_buffer_size,
    has_pedalboard_cache, reset_get_all_pedalboards_cache, update_cached_pedalboard_version,
    set_jack_buffer_size, get_jack_sample_rate, set_truebypass_value, set_process_name, reset_xruns
)

try:
    from mod.communication import token
except:
    token = None

# Global webserver state
class GlobalWebServerState:
    favorites = []

gState = GlobalWebServerState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    lv2_init()
    gState.favorites = safe_json_load(FAVORITES_JSON_FILE, list)
    if len(gState.favorites) > 0:
        uris = get_plugin_list()
        for uri in gState.favorites:
            if uri not in uris:
                gState.favorites.remove(uri)
    
    yield
    
    # Shutdown
    lv2_cleanup()

app = FastAPI(title="MOD UI API", version="0.1.0", lifespan=lifespan)

# Helper functions (simplified)
def mod_squeeze(text):
    return text.replace("\\", "\\\\").replace("'", "\\'")

# Routes
@app.get("/system/prefs")
async def system_prefs():
    prefs = safe_json_load(PREFERENCES_JSON_FILE, dict)
    return prefs

@app.get("/system/info")
async def system_info():
    hwdesc = get_hardware_descriptor()
    uname = os.uname()

    if os.path.exists("/etc/mod-release/system"):
        with open("/etc/mod-release/system") as fh:
            sysdate = fh.readline().replace("generated=","").split(" at ",1)[0].strip()
    else:
        sysdate = "Unknown"

    info = {
        "hwname": hwdesc.get('name', "Unknown"),
        "architecture": hwdesc.get('architecture', "Unknown"),
        "cpu": MODEL_CPU or hwdesc.get('cpu', "Unknown"),
        "platform": hwdesc.get('platform', "Unknown"),
        "bin_compat": hwdesc.get('bin-compat', "Unknown"),
        "model": MODEL_TYPE or hwdesc.get('model', "Unknown"),
        "sysdate": sysdate,
        "python": {
            "version" : sys.version
        },
        "uname": {
            "machine": uname.machine,
            "release": uname.release,
            "sysname": uname.sysname,
            "version": uname.version
        }
    }

    return info

@app.get("/effects/list")
async def effect_list():
    data = get_all_plugins()
    return data

@app.get("/pedalboards/list")
async def pedalboard_list():
    allpedals = get_all_pedalboards(kPedalboardInfoBoth)
    default_pb = next((p for p in allpedals if p['bundle'] == DEFAULT_PEDALBOARD), None)
    if default_pb:
        default_pb['title'] = "Default"
        default_pb['broken'] = False
    return allpedals

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            parts = data.split(" ", 1)
            cmd = parts[0]
            msg = parts[1] if len(parts) > 1 else ""

            if cmd == "data_ready":
                counter = int(msg)
                SESSION.ws_data_ready(counter)
            elif cmd == "param_set":
                data_parts = msg.split(" ", 2)
                port = data_parts[0]
                value = float(data_parts[1])
                SESSION.ws_parameter_set(port, value, websocket)
            elif cmd == "patch_get":
                data_parts = msg.split(" ", 1)
                inst = data_parts[0]
                uri = data_parts[1]
                SESSION.ws_patch_get(inst, uri, websocket)
            elif cmd == "patch_set":
                data_parts = msg.split(" ", 3)
                inst = data_parts[0]
                uri = data_parts[1]
                vtype = data_parts[2]
                value = data_parts[3]
                SESSION.ws_patch_set(inst, uri, vtype, value, websocket)
            elif cmd == "plugin_pos":
                data_parts = msg.split(" ", 2)
                inst = data_parts[0]
                x = float(data_parts[1])
                y = float(data_parts[2])
                SESSION.ws_plugin_position(inst, x, y, websocket)
            elif cmd == "pb_size":
                data_parts = msg.split(" ", 1)
                width = int(float(data_parts[0]))
                height = int(float(data_parts[1]))
                SESSION.ws_pedalboard_size(width, height)
            elif cmd == "link_enable":
                SESSION.host.set_link_enabled()
            elif cmd == "midi_clock_slave_enable":
                SESSION.host.set_midi_clock_slave_enabled()
            elif cmd == "set_internal_transport_source":
                SESSION.host.set_internal_transport_source()
            elif cmd == "transport-bpb":
                bpb = float(msg)
                SESSION.host.set_transport_bpb(bpb, True, True, False, False)
            elif cmd == "transport-bpm":
                bpm = float(msg)
                SESSION.host.set_transport_bpm(bpm, True, True, False, False)
            elif cmd == "transport-rolling":
                rolling = bool(int(msg))
                SESSION.host.set_transport_rolling(rolling, True, True, False, False)
            elif cmd == "show_external_ui":
                inst = msg
                SESSION.ws_show_external_ui(inst)
            else:
                print("Unexpected command received over websocket")

    except WebSocketDisconnect:
        websockets.remove(websocket)

@app.get("/ping")
async def ping():
    start = time.time()
    # Simplified ping logic
    online = True  # Assume online for now
    end = time.time()
    ihm_time = int((end - start) * 1000) or 1
    return {
        'ihm_online': online,
        'ihm_time': ihm_time,
    }

@app.post("/favorites/add")
async def favorites_add(uri: str = Form(...)):
    # safety check, no duplicates please
    if uri in gState.favorites:
        return False

    # add and save
    gState.favorites.append(uri)
    with TextFileFlusher(FAVORITES_JSON_FILE) as fh:
        json.dump(gState.favorites, fh)

    return True

@app.get("/effect/connect/{ports:path}")
async def effect_connect(ports: str):
    port_from, port_to = ports.split(',')
    ok = await asyncio.get_event_loop().run_in_executor(None, SESSION.web_connect, port_from, port_to)
    return ok

@app.post("/snapshot/save")
async def snapshot_save():
    ok = SESSION.host.snapshot_save()
    SESSION.host.save_snapshots_to_disk()
    return ok

@app.get("/banks")
async def bank_load():
    # Banks have only bundle and title of each pedalboard, which is the necessary information for the HMI.
    # But for the GUI we need to know information about the used pedalboards

    # First we get all pedalboard info
    allpedals = get_all_pedalboards(kPedalboardInfoBoth)
    pedalboards_data = dict((os.path.abspath(pb['bundle']), pb) for pb in allpedals)

    # List the broken pedalboards, we do not want to show those
    broken_pedalboards = tuple(pb['bundle'] for pb in allpedals if pb['broken'])

    # Get the banks using our broken pedalboards filter
    banks = list_banks(broken_pedalboards)

    # Put the full pedalboard info into banks
    for bank in banks:
        bank_pedalboards = []
        for pb in bank['pedalboards']:
            bundle = os.path.abspath(pb['bundle'])
            try:
                pbdata = pedalboards_data[bundle]
            except KeyError:
                continue
            bank_pedalboards.append(pbdata)
        bank['pedalboards'] = bank_pedalboards

    return banks

@app.get("/banks/save")
async def bank_save(request: Request):
    banks = await request.json()
    save_banks(banks)
    return True

# Template routes
@app.get("/", response_class=HTMLResponse)
@app.get("/{path}.html", response_class=HTMLResponse)
async def template_handler(request: Request, path: str = "index", v: Optional[str] = None):
    if path == "sdk":
        # Redirect to :9000
        return HTMLResponse(content="<script>window.location.href='http://localhost:9000';</script>", status_code=302)
    elif path == "allguis":
        return HTMLResponse(content="<script>window.location.href='/allguis.html?v=%s';</script>" % (v or "1.0"), status_code=302)
    elif path == "settings":
        return HTMLResponse(content="<script>window.location.href='/settings.html?v=%s';</script>" % (v or "1.0"), status_code=302)

    if path == "index":
        # Render index template with context
        user_id = safe_json_load(USER_ID_JSON_FILE, dict)
        pbname = SESSION.host.pedalboard_name
        prname = SESSION.host.snapshot_name()
        fullpbname = pbname or UNTITLED_PEDALBOARD_NAME
        if prname:
            fullpbname += " - " + prname

        hwdesc = get_hardware_descriptor()

        context = {
            'default_icon_template': mod_squeeze(DEFAULT_ICON_TEMPLATE),
            'default_settings_template': mod_squeeze(DEFAULT_SETTINGS_TEMPLATE),
            'default_pedalboard': mod_squeeze(DEFAULT_PEDALBOARD),
            'cloud_url': CLOUD_HTTP_ADDRESS,
            'cloud_labs_url': CLOUD_LABS_HTTP_ADDRESS,
            'plugins_url': PLUGINS_HTTP_ADDRESS,
            'pedalboards_url': PEDALBOARDS_HTTP_ADDRESS,
            'pedalboards_labs_url': PEDALBOARDS_LABS_HTTP_ADDRESS,
            'controlchain_url': CONTROLCHAIN_HTTP_ADDRESS,
            'hardware_profile': "",  # TODO
            'version': v or "1.0",
            'bin_compat': hwdesc.get('bin-compat', "Unknown"),
            'codec_truebypass': 'true' if hwdesc.get('codec_truebypass', False) else 'false',
            'factory_pedalboards': hwdesc.get('factory_pedalboards', False),
            'platform': hwdesc.get('platform', "Unknown"),
            'addressing_pages': int(hwdesc.get('addressing_pages', 0)),
            'lv2_plugin_dir': mod_squeeze(LV2_PLUGIN_DIR),
            'bundlepath': mod_squeeze(SESSION.host.pedalboard_path),
            'title': mod_squeeze(pbname),
            'size': json.dumps(SESSION.host.pedalboard_size),
            'fulltitle': fullpbname,
            'titleblend': '' if SESSION.host.pedalboard_name else 'blend',
            'dev_api_class': 'dev_api' if DEV_API else '',
            'using_desktop': 'true' if DESKTOP else 'false',
            'using_mod': 'true' if DEVICE_KEY and hwdesc.get('platform', None) is not None else 'false',
            'user_name': mod_squeeze(user_id.get("name", "")),
            'user_email': mod_squeeze(user_id.get("email", "")),
            'favorites': json.dumps(gState.favorites),
            'preferences': json.dumps(SESSION.prefs.prefs),
            'bufferSize': get_jack_buffer_size(),
            'sampleRate': get_jack_sample_rate(),
        }
        return templates.TemplateResponse("index.html", {"request": request, **context})

    elif path == "pedalboard":
        bundlepath = request.query_params.get('bundlepath')
        # TODO: render pedalboard template
        return templates.TemplateResponse("pedalboard.html", {"request": request})

    elif path == "allguis":
        context = {'version': v or "1.0"}
        return templates.TemplateResponse("allguis.html", {"request": request, **context})

    elif path == "settings":
        hwdesc = get_hardware_descriptor()
        prefs = safe_json_load(PREFERENCES_JSON_FILE, dict)
        context = {
            'cloud_url': CLOUD_HTTP_ADDRESS,
            'controlchain_url': CONTROLCHAIN_HTTP_ADDRESS,
            'version': v or "1.0",
            'hmi_eeprom': 'true' if hwdesc.get('hmi_eeprom', False) else 'false',
            'preferences': json.dumps(prefs),
            'bufferSize': get_jack_buffer_size(),
            'sampleRate': get_jack_sample_rate(),
        }
        return templates.TemplateResponse("settings.html", {"request": request, **context})

    # Default to static file
    return FileResponse(os.path.join(HTML_DIR, f"{path}.html"))

@app.get("/{path:path}")
async def static_files(path: str):
    file_path = os.path.join(HTML_DIR, path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)