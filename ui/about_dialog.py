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

import sys
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from ui import constants as C
from ui.theme_manager import ThemeManager


def _read_version() -> str:
    """Read project version from pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib  # type: ignore[no-redef]

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


class AboutDialog(QDialog):
    """About dialog with project information, contacts, and license."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(C.ABOUT_DIALOG_TITLE)
        self.setMinimumSize(620, 520)
        self.theme_manager = ThemeManager.instance()
        self.theme_manager.register(self, role="dialog")
        self._version = _read_version()
        self.setup_ui()

    def setup_ui(self) -> None:
        """Sets up the dialog UI."""
        layout = QVBoxLayout()

        text_edit = QTextBrowser()
        text_edit.setReadOnly(True)
        text_edit.setOpenExternalLinks(True)
        text_edit.setHtml(self._build_html())

        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def _build_html(self) -> str:
        """Builds the About dialog HTML content."""
        return f"""
        <h2 style="margin-bottom: 2px;">Compareror</h2>
        <p style="margin-top: 0;"><b>Version:</b> {self._version}</p>

        <h3>About the Project</h3>
        <p>
            Compareror is a desktop application for efficient directory synchronization
            with visual comparison, regex-based filtering, and rollback capabilities.
            Built with PyQt6, it uses a Strategy pattern architecture with pluggable
            algorithms for scanning, hashing, diffing, and executing sync operations.
        </p>

        <h3>Author</h3>
        <p><b>nekoClangUage</b></p>

        <h3>Contacts</h3>
        <table cellspacing="0" cellpadding="2" style="border: none;">
            <tr>
                <td><b>Email:</b></td>
                <td><a href="mailto:example@example.com">example@example.com</a></td>
            </tr>
            <tr>
                <td><b>Website:</b></td>
                <td><a href="https://example.com">https://example.com</a></td>
            </tr>
            <tr>
                <td><b>Twitter/X:</b></td>
                <td><a href="https://x.com/example">@example</a></td>
            </tr>
            <tr>
                <td><b>Telegram:</b></td>
                <td><a href="https://t.me/example">@example</a></td>
            </tr>
        </table>

        <h3>GitHub Repository</h3>
        <p>
            <a href="https://github.com/yourusername/compareror">
                https://github.com/yourusername/compareror
            </a>
        </p>

        <h3>License</h3>
        <p>
            This project is licensed under the
            <b>GNU Affero General Public License v3.0</b> (AGPL-3.0-or-later).
        </p>
        <p>
            You are free to use, modify, and distribute this software under the terms
            of the AGPL-3.0. If you modify this software and make it available over a
            network, you must release your modifications under the same license.
        </p>
        <p>
            Full license text:
            <a href="https://www.gnu.org/licenses/agpl-3.0.html">
                https://www.gnu.org/licenses/agpl-3.0.html
            </a>
        </p>

        <h3>Acknowledgments</h3>
        <ul>
            <li>Built with <a href="https://www.riverbankcomputing.com/software/pyqt/">PyQt6</a></li>
            <li>Linted &amp; formatted with <a href="https://github.com/astral-sh/ruff">Ruff</a></li>
            <li>Architecture diagrams in <a href="https://plantuml.com/">PlantUML</a></li>
        </ul>

        <hr>
        <p style="font-size: small; color: gray;">
            &copy; 2026 nekoClangUage. All rights reserved under AGPL-3.0-or-later.
        </p>
        """
