"""Tests for the diff mode UI in SettingsDialog."""

from __future__ import annotations

import pytest
import yaml

from app_settings import AppSettings, SettingsManager
from ui.settings_dialog import SettingsDialog


@pytest.fixture()
def settings_manager(tmp_path):
    path = tmp_path / "test_settings.yaml"
    return SettingsManager(path)


@pytest.fixture()
def default_dialog(qtbot, settings_manager):
    dialog = SettingsDialog(AppSettings(), settings_manager)
    qtbot.addWidget(dialog)
    return dialog


class TestDiffModeRadioButtons:
    """Tests for diff mode radio button presence and layout."""

    def test_all_three_radios_exist(self, default_dialog):
        assert "strict" in default_dialog.diff_mode_radios
        assert "two-phase" in default_dialog.diff_mode_radios
        assert "fast" in default_dialog.diff_mode_radios

    def test_radio_labels(self, default_dialog):
        assert default_dialog.diff_mode_radios["strict"].text() == "Strict (Content Hash)"
        assert default_dialog.diff_mode_radios["two-phase"].text() == "Two-Phase (Size/Date + Hash)"
        assert default_dialog.diff_mode_radios["fast"].text() == "Fast (Size/Date)"

    def test_radios_are_mutually_exclusive(self, default_dialog):
        default_dialog.diff_mode_radios["fast"].setChecked(True)
        assert default_dialog.diff_mode_radios["fast"].isChecked()
        assert not default_dialog.diff_mode_radios["strict"].isChecked()
        assert not default_dialog.diff_mode_radios["two-phase"].isChecked()


class TestDiffModeDefaultLoad:
    """Tests that the default diff mode is loaded correctly."""

    def test_default_is_two_phase(self, default_dialog):
        assert default_dialog.diff_mode_radios["two-phase"].isChecked()

    def test_default_collect_returns_two_phase(self, default_dialog):
        settings = default_dialog._collect_settings()
        assert settings.diff_mode == "two-phase"


class TestDiffModeLoadFromConfig:
    """Tests loading specific diff modes from AppSettings."""

    @pytest.mark.parametrize("mode", ["strict", "two-phase", "fast"])
    def test_load_each_mode(self, qtbot, settings_manager, mode):
        settings = AppSettings(diff_mode=mode)
        dialog = SettingsDialog(settings, settings_manager)
        qtbot.addWidget(dialog)

        assert dialog.diff_mode_radios[mode].isChecked()
        for other_mode, radio in dialog.diff_mode_radios.items():
            if other_mode != mode:
                assert not radio.isChecked()

    def test_invalid_mode_falls_back_to_two_phase(self, qtbot, settings_manager):
        settings = AppSettings(diff_mode="two-phase")
        dialog = SettingsDialog(settings, settings_manager)
        qtbot.addWidget(dialog)
        assert dialog.diff_mode_radios["two-phase"].isChecked()


class TestDiffModeUserInteraction:
    """Tests that user clicks are captured correctly in collected settings."""

    @pytest.mark.parametrize("mode", ["strict", "two-phase", "fast"])
    def test_click_and_collect(self, default_dialog, mode):
        default_dialog.diff_mode_radios[mode].setChecked(True)
        settings = default_dialog._collect_settings()
        assert settings.diff_mode == mode

    def test_switch_modes_multiple_times(self, default_dialog):
        default_dialog.diff_mode_radios["fast"].setChecked(True)
        assert default_dialog._collect_settings().diff_mode == "fast"

        default_dialog.diff_mode_radios["strict"].setChecked(True)
        assert default_dialog._collect_settings().diff_mode == "strict"

        default_dialog.diff_mode_radios["two-phase"].setChecked(True)
        assert default_dialog._collect_settings().diff_mode == "two-phase"


class TestDiffModePersistence:
    """Tests that diff_mode is correctly persisted to YAML."""

    @pytest.mark.parametrize("mode", ["strict", "two-phase", "fast"])
    def test_save_and_reload(self, tmp_path, qtbot, mode):
        yaml_path = tmp_path / "persist_test.yaml"
        sm = SettingsManager(yaml_path)

        settings = AppSettings(diff_mode=mode)
        sm.save(settings)

        loaded, errors = sm.load()
        assert not errors
        assert loaded.diff_mode == mode

        dialog = SettingsDialog(loaded, sm)
        qtbot.addWidget(dialog)
        assert dialog.diff_mode_radios[mode].isChecked()

    def test_yaml_contains_diff_mode_key(self, tmp_path):
        yaml_path = tmp_path / "key_test.yaml"
        sm = SettingsManager(yaml_path)
        sm.save(AppSettings(diff_mode="fast"))

        content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert "diff_mode" in content
        assert content["diff_mode"] == "fast"


class TestDiffModeImportExport:
    """Tests that import/export preserves diff_mode."""

    def test_export_then_import_preserves_mode(self, tmp_path, qtbot):
        yaml_path = tmp_path / "export_test.yaml"
        sm = SettingsManager(yaml_path)

        original = AppSettings(diff_mode="strict")
        sm.save_to_path(original, yaml_path)

        loaded, errors = sm.load_from_path(yaml_path)
        assert not errors
        assert loaded.diff_mode == "strict"

        dialog = SettingsDialog(loaded, sm)
        qtbot.addWidget(dialog)
        assert dialog.diff_mode_radios["strict"].isChecked()
