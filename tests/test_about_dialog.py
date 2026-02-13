# Copyright (C) 2026 nekoClangUage
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import pytest
from PyQt6.QtWidgets import QPushButton, QTextBrowser

from ui.about_dialog import AboutDialog, _read_version


class TestReadVersion:
    """Tests for the _read_version helper."""

    def test_returns_string(self):
        version = _read_version()
        assert isinstance(version, str)

    def test_version_is_not_empty(self):
        version = _read_version()
        assert version != ""

    def test_version_matches_pyproject(self):
        version = _read_version()
        assert version == "1.0.0"


class TestAboutDialog:
    """Tests for the AboutDialog widget."""

    @pytest.fixture()
    def dialog(self, qtbot):
        dlg = AboutDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_dialog_creation(self, dialog):
        assert dialog is not None

    def test_window_title(self, dialog):
        assert dialog.windowTitle() == "About Compareror"

    def test_minimum_size(self, dialog):
        assert dialog.minimumWidth() >= 620
        assert dialog.minimumHeight() >= 520

    def test_has_close_button(self, dialog):
        buttons = dialog.findChildren(QPushButton)
        labels = [b.text() for b in buttons]
        assert "Close" in labels

    def test_has_text_edit(self, dialog):
        text_edits = dialog.findChildren(QTextBrowser)
        assert len(text_edits) == 1
        assert text_edits[0].isReadOnly()

    def test_contains_version(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "1.0.0" in html

    def test_contains_project_name(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "Compareror" in html

    def test_contains_author(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "nekoClangUage" in html

    def test_contains_license_info(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "AGPL" in html

    def test_contains_github_link(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "github.com" in html

    def test_contains_contact_sections(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "Email" in html
        assert "Website" in html

    def test_contains_acknowledgments(self, dialog):
        text_edit = dialog.findChildren(QTextBrowser)[0]
        html = text_edit.toHtml()
        assert "PyQt6" in html
        assert "Ruff" in html

    def test_close_button_accepts(self, dialog, qtbot):
        buttons = dialog.findChildren(QPushButton)
        close_btn = next(b for b in buttons if b.text() == "Close")
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            close_btn.click()
