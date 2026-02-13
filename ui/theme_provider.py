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

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette


class AppThemeProvider:
    def build_stylesheet(self, theme: str) -> str:
        if theme == "light":
            return """
            QWidget {
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
            }
            QMainWindow[themeRole="main"] {
                background-color: rgba(245, 247, 252, 255);
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(245, 247, 252, 245),
                    stop: 0.55 rgba(233, 237, 247, 240),
                    stop: 1 rgba(221, 226, 238, 235)
                );
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget QWidget {
                background: transparent;
            }
            QDialog[themeRole="dialog"] {
                background: rgba(248, 250, 255, 245);
            }
            QDialog[themeRole="dialog"] QTextEdit {
                background-color: rgba(255, 255, 255, 240);
                color: #1c1f2a;
                border: 1px solid rgba(150, 160, 175, 200);
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                background-color: rgba(67, 113, 178, 210);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(77, 128, 198, 235);
            }
            QPushButton:pressed {
                background-color: rgba(52, 96, 156, 235);
            }
            QPushButton:disabled {
                background-color: rgba(170, 180, 196, 160);
                color: rgba(80, 80, 90, 140);
            }
            QPushButton#bottomActionButton {
                padding: 8px 18px;
                font-size: 13px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 230);
                color: #1c1f2a;
                border: 1px solid rgba(150, 160, 175, 200);
                border-radius: 5px;
                padding: 6px 8px;
            }
            QLineEdit:read-only {
                background-color: rgba(245, 246, 250, 210);
            }
            QMenuBar {
                background: rgba(230, 235, 247, 255);
                color: rgba(35, 38, 48, 235);
                padding: 4px;
                border-bottom: 2px solid rgba(160, 170, 190, 200);
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background-color: rgba(120, 150, 205, 160);
                color: rgba(20, 22, 30, 235);
            }
            QMenu {
                background: rgba(245, 247, 252, 255);
                color: rgba(35, 38, 48, 235);
                border: 1px solid rgba(160, 170, 190, 200);
                border-radius: 8px;
            }
            QMenu::item {
                padding: 8px 14px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(120, 150, 205, 175);
                color: rgba(20, 22, 30, 235);
            }
            QTreeWidget {
                background-color: rgba(250, 251, 255, 245);
                border: 1px solid rgba(160, 170, 190, 200);
                border-radius: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
                color: #1c1f2a;
            }
            QTreeWidget::item {
                padding: 4px;
                min-height: 20px;
            }
            QTreeWidget::item:selected {
                background-color: rgba(120, 150, 205, 175);
            }
            QTreeWidget::item:hover {
                background-color: rgba(180, 196, 226, 140);
            }
            QLabel {
                color: #1c1f2a;
                padding: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            QGroupBox {
                color: #1c1f2a;
                border: 1px solid rgba(160, 170, 190, 200);
                border-radius: 8px;
                margin-top: 12px;
                padding: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QTableWidget {
                background-color: rgba(255, 255, 255, 235);
                border: 1px solid rgba(160, 170, 190, 200);
                border-radius: 6px;
                gridline-color: rgba(200, 205, 220, 200);
            }
            QHeaderView::section {
                background-color: rgba(225, 231, 244, 235);
                color: rgba(25, 28, 36, 230);
                padding: 6px;
                border: none;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 230);
                color: #1c1f2a;
                border: 1px solid rgba(160, 170, 190, 200);
                border-radius: 4px;
                padding: 3px 6px;
            }
            QSplitter::handle {
                background-color: rgba(170, 180, 196, 180);
            }
            QScrollBar:vertical {
                background-color: rgba(210, 215, 228, 170);
                width: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(120, 150, 205, 190);
                min-height: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(90, 130, 195, 200);
            }
            QScrollBar::handle:vertical:pressed {
                background-color: rgba(70, 110, 175, 220);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: rgba(210, 215, 228, 170);
                height: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(120, 150, 205, 190);
                min-width: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(90, 130, 195, 200);
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: rgba(70, 110, 175, 220);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

        if theme == "dracula":
            return """
            QWidget {
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
            }
            QMainWindow[themeRole="main"] {
                background-color: #282A36;
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #282A36,
                    stop: 0.55 #2A2D3A,
                    stop: 1 #21222C
                );
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget QWidget {
                background: transparent;
            }
            QDialog[themeRole="dialog"] {
                background: #282A36;
            }
            QDialog[themeRole="dialog"] QTextEdit {
                background-color: #44475A;
                color: #F8F8F2;
                border: 1px solid #6272A4;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                background-color: #BD93F9;
                color: #F8F8F2;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #FF79C6;
            }
            QPushButton:pressed {
                background-color: #9580FF;
            }
            QPushButton:disabled {
                background-color: #6272A4;
                color: #9F9F9F;
            }
            QPushButton#bottomActionButton {
                padding: 8px 18px;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #44475A;
                color: #F8F8F2;
                border: 1px solid #6272A4;
                border-radius: 5px;
                padding: 6px 8px;
            }
            QLineEdit:read-only {
                background-color: #3A3D4A;
            }
            QMenuBar {
                background: #21222C;
                color: #F8F8F2;
                padding: 4px;
                border-bottom: 2px solid #BD93F9;
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background-color: #BD93F9;
                color: #F8F8F2;
            }
            QMenu {
                background: #282A36;
                color: #F8F8F2;
                border: 1px solid #BD93F9;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 8px 14px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #BD93F9;
                color: #F8F8F2;
            }
            QTreeWidget {
                background-color: #282A36;
                border: 1px solid #6272A4;
                border-radius: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
                color: #F8F8F2;
            }
            QTreeWidget::item {
                padding: 4px;
                min-height: 20px;
            }
            QTreeWidget::item:selected {
                background-color: #BD93F9;
            }
            QTreeWidget::item:hover {
                background-color: #44475A;
            }
            QLabel {
                color: #F8F8F2;
                padding: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            QGroupBox {
                color: #F8F8F2;
                border: 1px solid #6272A4;
                border-radius: 8px;
                margin-top: 12px;
                padding: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QTableWidget {
                background-color: #282A36;
                border: 1px solid #6272A4;
                border-radius: 6px;
                gridline-color: #6272A4;
                color: #F8F8F2;
            }
            QHeaderView::section {
                background-color: #44475A;
                color: #F8F8F2;
                padding: 6px;
                border: none;
            }
            QComboBox {
                background-color: #44475A;
                color: #F8F8F2;
                border: 1px solid #6272A4;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QSplitter::handle {
                background-color: #6272A4;
            }
            QScrollBar:vertical {
                background-color: #21222C;
                width: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #BD93F9;
                min-height: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #FF79C6;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #9580FF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #21222C;
                height: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #BD93F9;
                min-width: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #FF79C6;
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: #9580FF;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

        return """
            QWidget {
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
            }
            QMainWindow[themeRole="main"] {
                background-color: rgba(20, 25, 40, 255);
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(22, 36, 70, 205),
                    stop: 0.55 rgba(43, 43, 61, 200),
                    stop: 1 rgba(12, 12, 18, 215)
                );
            }
            QMainWindow[themeRole="main"] QWidget#centralWidget QWidget {
                background: transparent;
            }
            QDialog[themeRole="dialog"] {
                background: rgba(20, 22, 34, 240);
            }
            QDialog[themeRole="dialog"] QTextEdit {
                background-color: rgba(30, 30, 46, 200);
                color: #e0e0e0;
                border: 1px solid rgba(74, 74, 90, 210);
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton {
                background-color: rgba(107, 91, 149, 130);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(139, 123, 181, 160);
            }
            QPushButton:pressed {
                background-color: rgba(91, 75, 133, 175);
            }
            QPushButton:disabled {
                background-color: rgba(74, 74, 90, 110);
                color: rgba(224, 224, 224, 95);
            }
            QPushButton#bottomActionButton {
                padding: 8px 18px;
                font-size: 13px;
            }
            QLineEdit {
                background-color: rgba(30, 30, 46, 95);
                color: #e0e0e0;
                border: 1px solid rgba(74, 74, 90, 200);
                border-radius: 5px;
                padding: 6px 8px;
            }
            QLineEdit:read-only {
                background-color: rgba(30, 30, 46, 75);
            }
            QMenuBar {
                background: rgba(40, 70, 120, 255);
                color: rgba(240, 245, 255, 225);
                padding: 4px;
                border-bottom: 2px solid rgba(107, 91, 149, 180);
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QMenuBar::item:selected {
                background-color: rgba(107, 91, 149, 155);
                color: rgba(255, 255, 255, 235);
            }
            QMenu {
                background: rgba(20, 25, 40, 175);
                color: rgba(235, 240, 255, 230);
                border: 1px solid rgba(107, 91, 149, 190);
                border-radius: 8px;
            }
            QMenu::item {
                padding: 8px 14px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(107, 91, 149, 175);
                color: white;
            }
            QTreeWidget {
                background-color: rgba(30, 30, 46, 240);
                border: 1px solid rgba(74, 74, 90, 210);
                border-radius: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 13px;
                color: #e0e0e0;
            }
            QTreeWidget::item {
                padding: 4px;
                min-height: 20px;
            }
            QTreeWidget::item:selected {
                background-color: rgba(107, 91, 149, 180);
            }
            QTreeWidget::item:hover {
                background-color: rgba(58, 58, 74, 160);
            }
            QLabel {
                color: #e0e0e0;
                padding: 5px;
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 1px solid rgba(74, 74, 90, 200);
                border-radius: 8px;
                margin-top: 12px;
                padding: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QTableWidget {
                background-color: rgba(30, 30, 46, 210);
                border: 1px solid rgba(74, 74, 90, 210);
                border-radius: 6px;
                gridline-color: rgba(90, 90, 110, 180);
                color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: rgba(45, 55, 90, 220);
                color: rgba(235, 240, 255, 230);
                padding: 6px;
                border: none;
            }
            QComboBox {
                background-color: rgba(30, 30, 46, 95);
                color: #e0e0e0;
                border: 1px solid rgba(74, 74, 90, 200);
                border-radius: 4px;
                padding: 3px 6px;
            }
            QSplitter::handle {
                background-color: rgba(74, 74, 90, 170);
            }
            QScrollBar:vertical {
                background-color: rgba(30, 30, 46, 120);
                width: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(107, 91, 149, 185);
                min-height: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(139, 123, 181, 200);
            }
            QScrollBar::handle:vertical:pressed {
                background-color: rgba(91, 75, 133, 210);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: rgba(30, 30, 46, 120);
                height: 16px;
                border: none;
                border-radius: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(107, 91, 149, 185);
                min-width: 30px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(139, 123, 181, 200);
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: rgba(91, 75, 133, 210);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

    def build_palette(self, theme: str) -> QPalette:
        palette = QPalette()
        if theme == "light":
            palette.setColor(QPalette.ColorRole.WindowText, QColor(28, 31, 42))
            palette.setColor(QPalette.ColorRole.Text, QColor(28, 31, 42))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Base, QColor(245, 247, 252))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(230, 235, 245))
            palette.setColor(QPalette.ColorRole.Window, QColor(245, 247, 252))
            palette.setColor(QPalette.ColorRole.Button, QColor(67, 113, 178))
        elif theme == "dracula":
            palette.setColor(QPalette.ColorRole.WindowText, QColor(248, 248, 242))
            palette.setColor(QPalette.ColorRole.Text, QColor(248, 248, 242))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(248, 248, 242))
            palette.setColor(QPalette.ColorRole.Base, QColor(68, 71, 90))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 42, 54))
            palette.setColor(QPalette.ColorRole.Window, QColor(40, 42, 54))
            palette.setColor(QPalette.ColorRole.Button, QColor(189, 147, 249))
        else:  # dark
            palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
            palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 46))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 61))
            palette.setColor(QPalette.ColorRole.Window, QColor(20, 25, 40))
            palette.setColor(QPalette.ColorRole.Button, QColor(107, 91, 149))
        return palette
