import threading
from multiprocessing import Manager
from pathlib import Path

import pytest

from app_settings import SettingsManager
from sync.directory_sync_model import DirectorySyncModel


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    """
    Globally patch SettingsManager to use a temporary file instead of the local settings.yaml
    when no path is provided. This ensures tests are independent of user configuration.
    """
    # Create a dummy settings file in the temp dir so it exists but is empty/default
    settings_path = tmp_path / "test_settings_global.yaml"

    # Store original init to call it
    original_init = SettingsManager.__init__

    def mock_init(self, path=None):
        # If no path is provided (default behavior), use the temp path
        if path is None:
            path = settings_path
        original_init(self, path)

    monkeypatch.setattr(SettingsManager, "__init__", mock_init)
    return settings_path


@pytest.fixture()
def temp_dir(tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    def write_file(base: Path, rel_path: Path, content: str) -> Path:
        path = base / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return {"root": tmp_path, "dir1": dir1, "dir2": dir2, "write_file": write_file}


@pytest.fixture()
def sync_model():
    return DirectorySyncModel()


@pytest.fixture()
def stop_events():
    stop_event = threading.Event()
    manager = Manager()
    mp_stop_event = manager.Event()
    yield stop_event, mp_stop_event
    manager.shutdown()


@pytest.fixture()
def backup_dir(tmp_path):
    path = tmp_path / "backup"
    path.mkdir()
    return path
