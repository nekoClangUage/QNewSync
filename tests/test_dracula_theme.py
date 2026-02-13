"""
Tests for Dracula theme implementation: theme switching, validation, and UI integration.
"""

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from app_settings import AppSettings, SettingsManager, settings_from_dict
from ui.theme_manager import ThemeManager
from ui.theme_provider import AppThemeProvider


class TestDraculaTheme:
    """Test Dracula theme functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])

        self.theme_manager = ThemeManager.instance()
        self.provider = AppThemeProvider()
        self.theme_manager.set_provider(self.provider)

    def test_dracula_theme_validation(self):
        """Test Dracula theme is recognized as valid."""
        settings, errors = settings_from_dict({"theme": "dracula"})
        assert settings.theme == "dracula"
        assert errors == []

    def test_dracula_theme_normalization(self):
        """Test Dracula theme normalization in ThemeManager."""
        # Test various case variations
        assert ThemeManager._normalize_theme("dracula") == "dracula"
        assert ThemeManager._normalize_theme("DRACULA") == "dracula"
        assert ThemeManager._normalize_theme("DrAcUlA") == "dracula"

    def test_dracula_theme_provider_stylesheet(self):
        """Test Dracula stylesheet generation."""
        stylesheet = self.provider.build_stylesheet("dracula")
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        # Check for key Dracula colors
        assert "#282A36" in stylesheet  # Background
        assert "#BD93F9" in stylesheet  # Purple (primary)
        assert "#F8F8F2" in stylesheet  # Foreground
        assert "#FF79C6" in stylesheet  # Pink (hover)

    def test_dracula_theme_provider_palette(self):
        """Test Dracula palette generation."""
        palette = self.provider.build_palette("dracula")
        assert isinstance(palette, QPalette)

        # Check key color mappings
        window_color = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.Text)
        button_color = palette.color(QPalette.ColorRole.Button)

        # Verify Dracula colors are applied (using RGB values)
        assert window_color.getRgb()[:3] == (40, 42, 54)  # #282A36
        assert text_color.getRgb()[:3] == (248, 248, 242)  # #F8F8F2
        assert button_color.getRgb()[:3] == (189, 147, 249)  # #BD93F9

    def test_theme_manager_applies_dracula(self):
        """Test ThemeManager applies Dracula theme correctly."""
        # Apply Dracula theme
        self.theme_manager.apply_theme("dracula", animate=False)

        # Verify theme is set
        assert self.theme_manager.current_theme == "dracula"

        # Verify palette is applied to application
        app_palette = self.app.palette()
        window_color = app_palette.color(QPalette.ColorRole.Window)
        assert window_color.getRgb()[:3] == (40, 42, 54)  # #282A36

    def test_theme_switching_to_dracula(self):
        """Test switching from other themes to Dracula."""
        # Start with light theme
        self.theme_manager.apply_theme("light", animate=False)
        assert self.theme_manager.current_theme == "light"

        # Switch to Dracula
        self.theme_manager.apply_theme("dracula", animate=False)
        assert self.theme_manager.current_theme == "dracula"

        # Switch to dark
        self.theme_manager.apply_theme("dark", animate=False)
        assert self.theme_manager.current_theme == "dark"

        # Switch back to Dracula
        self.theme_manager.apply_theme("dracula", animate=False)
        assert self.theme_manager.current_theme == "dracula"

    def test_settings_persistence_dracula(self):
        """Test Dracula theme persistence in settings."""
        import tempfile
        from pathlib import Path

        # Create temporary settings file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            settings_path = Path(f.name)

        try:
            # Save settings with Dracula theme
            settings = AppSettings(theme="dracula", ignore_hidden=True)
            manager = SettingsManager(settings_path)
            manager.save(settings)

            # Load settings back
            loaded_settings, errors = manager.load()
            assert loaded_settings.theme == "dracula"
            assert loaded_settings.ignore_hidden is True
            assert errors == []

        finally:
            # Clean up
            if settings_path.exists():
                settings_path.unlink()

    def test_dracula_theme_caching(self):
        """Test Dracula theme caching in ThemeManager."""
        # First call should generate and cache
        stylesheet1 = self.provider.build_stylesheet("dracula")
        palette1 = self.provider.build_palette("dracula")

        # Second call should use cache
        stylesheet2 = self.provider.build_stylesheet("dracula")
        palette2 = self.provider.build_palette("dracula")

        # Results should be identical
        assert stylesheet1 == stylesheet2
        assert palette1.color(QPalette.ColorRole.Window).getRgb() == \
               palette2.color(QPalette.ColorRole.Window).getRgb()

    def test_invalid_theme_fallback(self):
        """Test invalid theme falls back to dark, not Dracula."""
        settings, errors = settings_from_dict({"theme": "nonexistent"})
        assert settings.theme == "dark"  # Should fallback to dark
        assert len(errors) > 0
        assert any("nonexistent" in e for e in errors)


class TestDraculaThemeIntegration:
    """Integration tests for Dracula theme with UI components."""

    def setup_method(self):
        """Set up test environment."""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])

    def test_settings_dialog_dracula_selection(self):
        """Test Dracula theme selection in SettingsDialog."""
        from ui.settings_dialog import SettingsDialog

        # Create settings with Dracula theme
        settings = AppSettings(theme="dracula")
        manager = SettingsManager()

        # Create dialog
        dialog = SettingsDialog(settings, manager)

        # Verify Dracula radio is checked
        assert dialog.theme_radios["dracula"].isChecked()
        assert not dialog.theme_radios["dark"].isChecked()
        assert not dialog.theme_radios["light"].isChecked()

        # Test collecting settings
        collected_settings = dialog._collect_settings()
        assert collected_settings.theme == "dracula"

    def test_settings_dialog_theme_switching(self):
        """Test theme switching in SettingsDialog."""
        from ui.settings_dialog import SettingsDialog

        # Create settings with dark theme
        settings = AppSettings(theme="dark")
        manager = SettingsManager()

        # Create dialog
        dialog = SettingsDialog(settings, manager)

        # Initially dark should be checked
        assert dialog.theme_radios["dark"].isChecked()

        # Switch to Dracula
        dialog.theme_radios["dracula"].setChecked(True)

        # Verify collected settings
        collected_settings = dialog._collect_settings()
        assert collected_settings.theme == "dracula"

    def test_load_dracula_settings_in_dialog(self):
        """Test loading Dracula settings in dialog."""
        from ui.settings_dialog import SettingsDialog

        # Create settings with Dracula theme
        settings = AppSettings(theme="dracula", ignore_hidden=False, copy_empty_dirs=True)
        manager = SettingsManager()

        # Create dialog and load settings
        dialog = SettingsDialog(AppSettings(), manager)  # Start with defaults
        dialog._load_settings(settings)

        # Verify Dracula theme is selected
        assert dialog.theme_radios["dracula"].isChecked()
        assert dialog.ignore_hidden_checkbox.isChecked() is False
        assert dialog.copy_empty_dirs_checkbox.isChecked() is True
