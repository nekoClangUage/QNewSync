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

"""
Main application entry point for the directory synchronization app.
Entry point.
"""

import multiprocessing
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from sync.bootstrap import ensure_strategies_registered
from ui.main_window import MainWindow
from ui.theme_manager import ThemeManager
from ui.theme_provider import AppThemeProvider


def main():
    """Main function that starts the application."""
    ensure_strategies_registered()
    app = QApplication(sys.argv)

    # Set application icon
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    icon_path = base_path / "icon_for_program.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Set application style
    app.setStyle("Fusion")

    theme_manager = ThemeManager.instance()
    theme_manager.set_provider(AppThemeProvider())

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
