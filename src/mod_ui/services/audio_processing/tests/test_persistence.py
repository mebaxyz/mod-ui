import pytest

from mod_ui.services.audio_processing.modhost_bridge import ModHostBridge
from mod_ui.services.audio_processing.plugin_manager import PluginManager
from mod_ui.services.audio_processing.session_manager import SessionManager


@pytest.mark.asyncio
async def test_pedalboard_save_load_delete(tmp_path, monkeypatch):
    # Use a dedicated data dir for the test
    data_dir = tmp_path / "ap_data"
    monkeypatch.setenv("AUDIO_PROCESSING_DATA_DIR", str(data_dir))

    # Setup simulated modhost and plugin manager
    monkeypatch.setenv("SIMULATE_MODHOST", "true")
    mod = ModHostBridge()
    await mod.start()
    pm = PluginManager(mod, None)
    await pm.initialize()

    sm = SessionManager(pm, mod, None)

    # Create a pedalboard
    res = await sm.create_pedalboard("TestPB", "desc")
    saved = await sm.save_pedalboard()

    assert saved["status"] == "ok"
    saved_id = saved.get("saved_id")
    assert saved_id is not None

    # list
    from mod_ui.services.audio_processing import storage

    items = storage.list_pedalboards()
    assert any(x["id"] == saved_id for x in items)

    # load
    loaded = storage.load_pedalboard(saved_id)
    assert loaded is not None
    assert loaded.get("name") == "TestPB"

    # delete
    ok = storage.delete_pedalboard(saved_id)
    assert ok is True
    assert storage.load_pedalboard(saved_id) is None

    await mod.stop()


@pytest.mark.asyncio
async def test_export_import_pedalboard(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_PROCESSING_DATA_DIR", str(tmp_path / "ap_data"))
    monkeypatch.setenv("SIMULATE_MODHOST", "true")

    mod = ModHostBridge()
    await mod.start()
    pm = PluginManager(mod, None)
    await pm.initialize()
    sm = SessionManager(pm, mod, None)

    await sm.create_pedalboard("X", "y")
    saved = await sm.save_pedalboard()
    pb_id = saved.get("saved_id")

    out_file = tmp_path / "exported.json"

    # Export via storage
    from mod_ui.services.audio_processing import storage

    ok = storage.export_pedalboard(pb_id, str(out_file))
    assert ok is True

    # Import back
    res = storage.import_pedalboard(str(out_file))
    assert res is not None
    new_id, new_path = res
    assert storage.load_pedalboard(new_id) is not None

    await mod.stop()
