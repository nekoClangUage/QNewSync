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

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QRectF, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCursor, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QRegion
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app_settings import AppSettings, SettingsManager, compile_regex_rules
from sync.directory_sync_model import DirectorySyncModel
from sync.interfaces import SyncStats
from ui import constants as C
from ui.about_dialog import AboutDialog
from ui.help_dialog import HelpDialog
from ui.lazy_directory_tree import LazyDirectoryTreeWidget
from ui.report_dialog import ReportDialog
from ui.settings_dialog import SettingsDialog
from ui.theme_manager import ThemeManager
from ui.workers import CancelWorkerThread, CompareWorkerThread, SyncWorkerThread


class ClickableLineEdit(QLineEdit):
    clicked = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class RoundedMenu(QMenu):
    def __init__(self, title: str = "", parent: QWidget | None = None, radius: int = 10) -> None:
        super().__init__(title, parent)
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    def _apply_mask(self) -> None:
        rect = self.rect()
        if rect.isEmpty():
            return

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), float(self._radius), float(self._radius))
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_mask()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_mask()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.model = DirectorySyncModel()
        self.settings_manager = SettingsManager()
        self.settings = AppSettings()
        self.compiled_rules = []
        self.sync_thread: SyncWorkerThread | None = None
        self.compare_thread: CompareWorkerThread | None = None
        self.cancel_thread: CancelWorkerThread | None = None
        self.dir1_path: Path | None = None
        self.dir2_path: Path | None = None
        self.files_to_sync: set[Path] = set()
        self.files_only_in_dir2: set[Path] = set()
        self.theme_manager = ThemeManager.instance()
        self.cancel_requested = False

        self.report_dialog: ReportDialog | None = None
        self.current_stats: SyncStats | None = None

        self.setup_ui()
        self.theme_manager.register(self, role="main")
        self.load_settings()

    def setup_ui(self) -> None:
        """Sets up the main window UI."""
        self.setWindowTitle(C.WINDOW_TITLE)
        self.setMinimumSize(C.MIN_WINDOW_WIDTH, C.MIN_WINDOW_HEIGHT)

        central_widget = QWidget()
        central_widget.setObjectName(C.OBJ_CENTRAL_WIDGET)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)
        menubar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        directories_menu = RoundedMenu(C.MENU_DIRECTORIES, self)
        menubar.addMenu(directories_menu)
        choose_dir1_action = QAction(C.ACTION_CHOOSE_DIR_1, self)
        choose_dir1_action.triggered.connect(self.select_directory1)
        directories_menu.addAction(choose_dir1_action)

        choose_dir2_action = QAction(C.ACTION_CHOOSE_DIR_2, self)
        choose_dir2_action.triggered.connect(self.select_directory2)
        directories_menu.addAction(choose_dir2_action)

        settings_action = QAction(C.ACTION_SETTINGS, self)
        settings_action.triggered.connect(self.open_settings)
        menubar.addAction(settings_action)

        report_action = QAction(C.ACTION_REPORT, self)
        report_action.triggered.connect(self.show_report)
        menubar.addAction(report_action)

        help_menu = RoundedMenu(C.MENU_HELP, self)
        menubar.addMenu(help_menu)
        show_help_action = QAction(C.ACTION_SHOW_HELP, self)
        show_help_action.triggered.connect(self.show_help)
        help_menu.addAction(show_help_action)
        about_action = QAction(C.MENU_ABOUT, self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        paths_layout = QVBoxLayout()

        dir1_layout = QHBoxLayout()
        self.dir1_label = QLabel(C.LABEL_DIRECTORY_1)
        self.dir1_label.setMinimumWidth(100)
        self.dir1_path_display = ClickableLineEdit()
        self.dir1_path_display.setReadOnly(True)
        self.dir1_path_display.setPlaceholderText(C.PLACEHOLDER_SELECT_DIR)
        self.dir1_path_display.clicked.connect(self.select_directory1)
        dir1_layout.addWidget(self.dir1_label)
        dir1_layout.addWidget(self.dir1_path_display, stretch=1)

        dir2_layout = QHBoxLayout()
        self.dir2_label = QLabel(C.LABEL_DIRECTORY_2)
        self.dir2_label.setMinimumWidth(100)
        self.dir2_path_display = ClickableLineEdit()
        self.dir2_path_display.setReadOnly(True)
        self.dir2_path_display.setPlaceholderText(C.PLACEHOLDER_SELECT_DIR)
        self.dir2_path_display.clicked.connect(self.select_directory2)
        dir2_layout.addWidget(self.dir2_label)
        dir2_layout.addWidget(self.dir2_path_display, stretch=1)

        paths_layout.addLayout(dir1_layout)
        paths_layout.addLayout(dir2_layout)

        main_layout.addLayout(paths_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree1 = LazyDirectoryTreeWidget()
        self.tree1.set_header_label(C.LABEL_DIRECTORY_1)
        self.tree1.set_header_alignment(Qt.AlignmentFlag.AlignCenter)
        self.tree1.fileDoubleClicked.connect(self._on_file_double_clicked)
        splitter.addWidget(self.tree1)

        self.tree2 = LazyDirectoryTreeWidget()
        self.tree2.set_header_label(C.LABEL_DIRECTORY_2)
        self.tree2.set_header_alignment(Qt.AlignmentFlag.AlignCenter)
        self.tree2.fileDoubleClicked.connect(self._on_file_double_clicked)
        splitter.addWidget(self.tree2)

        splitter.setSizes([500, 500])
        main_layout.addWidget(splitter, stretch=1)

        status_layout = QHBoxLayout()
        self.status_label = QLabel(C.LABEL_READY)
        self.speed_label = QLabel("")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        status_layout.addWidget(self.status_label, stretch=1)
        status_layout.addWidget(self.speed_label, stretch=1)

        main_layout.addLayout(status_layout)

        buttons_layout = QHBoxLayout()

        self.sync_btn = QPushButton(C.BTN_SYNCHRONIZE)
        self.sync_btn.clicked.connect(self.start_synchronization)
        self.sync_btn.setEnabled(False)
        self.sync_btn.setObjectName(C.OBJ_BOTTOM_ACTION_BTN)

        self.stop_btn = QPushButton(C.BTN_STOP)
        self.stop_btn.clicked.connect(self.stop_synchronization)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setObjectName(C.OBJ_BOTTOM_ACTION_BTN)

        self.cancel_btn = QPushButton(C.BTN_CANCEL)
        self.cancel_btn.clicked.connect(self.cancel_synchronization)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setObjectName(C.OBJ_BOTTOM_ACTION_BTN)

        buttons_layout.addWidget(self.sync_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(buttons_layout)

        self.model.set_progress_callback(self.update_status)

        self.set_custom_cursor()

    def _set_action_buttons(self, *, sync: bool, stop: bool, cancel: bool) -> None:
        """Enable/disable action buttons consistently."""

        self.sync_btn.setEnabled(sync)
        self.stop_btn.setEnabled(stop)
        self.cancel_btn.setEnabled(cancel)

    def _safe_cleanup_thread(self, thread: QThread | None, timeout_ms: int = 5000) -> None:
        """Safely wait for a QThread to finish before releasing it."""
        if thread is not None and thread.isRunning():
            thread.wait(timeout_ms)

    def _start_cancel_thread(self) -> None:
        """Starts rollback worker, waiting for any previous instance."""

        self._safe_cleanup_thread(self.cancel_thread)

        self.cancel_thread = CancelWorkerThread(self.model)
        self.cancel_thread.finished.connect(self.on_cancel_finished)
        self.cancel_thread.progress.connect(self.update_status)
        self.cancel_thread.start()

    def set_custom_cursor(self) -> None:
        """Sets a custom cursor for the window."""
        cursor_size = 32
        pixmap = QPixmap(cursor_size, cursor_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(
            QPen(
                QColor(0, 0, 0),
                3,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(3, 3, 3, 22)
        painter.drawLine(3, 3, 14, 14)
        painter.drawLine(6, 20, 14, 14)

        painter.setPen(
            QPen(
                QColor(255, 255, 255),
                1,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(3, 3, 3, 22)
        painter.drawLine(3, 3, 14, 14)
        painter.drawLine(6, 20, 14, 14)

        painter.end()

        cursor = QCursor(pixmap, 3, 3)
        self.setCursor(cursor)

        central = self.centralWidget()
        if central:
            central.setCursor(cursor)
            for widget in central.findChildren(QWidget):
                widget.setCursor(cursor)

    def apply_styles(self, theme: str | None = None) -> None:
        """Applies UI styles."""
        theme = (theme or self.settings.theme).lower()
        self.theme_manager.apply_theme(theme)

    def load_settings(self) -> None:
        settings, errors = self.settings_manager.load()
        compiled_rules, compile_errors = compile_regex_rules(settings.regex_rules)
        self._apply_settings_state(settings, compiled_rules)

        all_errors = errors + compile_errors
        if all_errors:
            QMessageBox.warning(self, C.DIALOG_SETTINGS_WARNING, "\n".join(all_errors))

    def _apply_settings_state(self, settings: AppSettings, compiled_rules) -> None:
        self.settings = settings
        self.compiled_rules = compiled_rules
        self.model.set_filters(
            ignore_hidden=settings.ignore_hidden,
            copy_empty_dirs=settings.copy_empty_dirs,
            compiled_rules=compiled_rules,
        )
        self.model.set_diff_mode(settings.diff_mode)
        self._apply_tree_settings()
        self.apply_styles(settings.theme)

    def apply_settings(self, settings: AppSettings) -> None:
        compiled_rules, errors = compile_regex_rules(settings.regex_rules)
        if errors:
            QMessageBox.warning(self, C.DIALOG_SETTINGS_ERROR, "\n".join(errors))
            return

        self._apply_settings_state(settings, compiled_rules)

        try:
            self.settings_manager.save(settings)
        except OSError as exc:
            QMessageBox.warning(self, C.DIALOG_SETTINGS_ERROR, C.MSG_FAILED_SAVE_SETTINGS.format(exc))

        if self.dir1_path and self.dir2_path:
            self.compare_directories()
        else:
            self.load_trees()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.settings_manager, self)
        if dialog.exec() and dialog.applied_settings:
            self.apply_settings(dialog.applied_settings)

    def _apply_tree_settings(self) -> None:
        self.tree1.set_ignore_hidden(self.settings.ignore_hidden)
        self.tree2.set_ignore_hidden(self.settings.ignore_hidden)

    def select_directory1(self) -> None:
        """Selects directory 1."""
        directory = QFileDialog.getExistingDirectory(self, C.DIALOG_SELECT_DIR_1)
        if directory:
            self.dir1_path = Path(directory)
            self.dir1_path_display.setText(directory)
            self.dir1_path_display.setCursorPosition(0)
            self.load_trees()
            self.check_ready()

    def select_directory2(self) -> None:
        """Selects directory 2."""
        directory = QFileDialog.getExistingDirectory(self, C.DIALOG_SELECT_DIR_2)
        if directory:
            self.dir2_path = Path(directory)
            self.dir2_path_display.setText(directory)
            self.dir2_path_display.setCursorPosition(0)
            self.load_trees()
            self.check_ready()

    def check_ready(self) -> None:
        """Checks whether the app is ready to synchronize."""
        if self.dir1_path and self.dir2_path:
            try:
                self.model.set_directories(str(self.dir1_path), str(self.dir2_path))
                self.sync_btn.setEnabled(True)
                self.compare_directories()
            except ValueError as e:
                QMessageBox.warning(self, C.DIALOG_DIR_SELECTION_ERROR, str(e))
                self.sync_btn.setEnabled(False)
        else:
            self.sync_btn.setEnabled(False)

    def compare_directories(self) -> None:
        """Compares directories and updates the UI asynchronously."""
        if not self.dir1_path or not self.dir2_path:
            return

        self.model.set_directories(str(self.dir1_path), str(self.dir2_path))

        self.tree1.load_directory(self.dir1_path, compiled_rules=self.compiled_rules)
        self.tree2.load_directory(self.dir2_path)

        self.status_label.setText(C.LABEL_COMPARING)

        if self.compare_thread and self.compare_thread.isRunning():
            self.model.stop()
            self.compare_thread.wait(5000)
            self.model.reset_stop()

        self.compare_thread = CompareWorkerThread(self.model)
        self.compare_thread.finished.connect(self.on_compare_finished)
        self.compare_thread.progress.connect(self.update_status)
        self.compare_thread.start()

    def on_compare_finished(self, result: tuple) -> None:
        """Handler for the directory comparison completion."""
        files_to_copy, files_to_replace, files_only_in_dir2, _files_unchanged = result

        self.files_to_sync = set(files_to_copy.keys()) | set(files_to_replace.keys())
        self.files_only_in_dir2 = files_only_in_dir2

        if self.dir2_path:
            self.tree2.load_directory(self.dir2_path)
            self.tree2.set_highlight_group("sync", self.files_to_sync, C.COLOR_HIGHLIGHT_SYNC)
            self.tree2.set_highlight_group("only_dir2", self.files_only_in_dir2, C.COLOR_HIGHLIGHT_ONLY_DIR2)

        self.status_label.setText(C.LABEL_READY_TO_SYNC)

    def start_synchronization(self) -> None:
        """Starts synchronization."""
        if not self.dir1_path or not self.dir2_path:
            QMessageBox.warning(self, C.DIALOG_ERROR, C.MSG_SELECT_BOTH_DIRS)
            return

        self.cancel_requested = False
        self._set_action_buttons(sync=False, stop=True, cancel=True)
        self.status_label.setText(C.LABEL_SYNC_STARTED)
        self.speed_label.setText(C.LABEL_STARTING)

        # Reset report dialog if it exists to clear old data
        if self.report_dialog:
            self.report_dialog.close()
            self.report_dialog = None

        self.sync_thread = SyncWorkerThread(self.model)
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.progress.connect(self.update_status)
        self.sync_thread.stats_updated.connect(self.on_stats_updated)
        self.sync_thread.start()

    def show_report(self) -> None:
        """Shows the synchronization report dialog."""
        if not self.report_dialog:
            self.report_dialog = ReportDialog(self)
            # If we have current stats (even if finished), update the new dialog
            if self.current_stats:
                self.report_dialog.update_stats(self.current_stats)

        self.report_dialog.show()
        self.report_dialog.raise_()
        self.report_dialog.activateWindow()

    def on_stats_updated(self, stats: SyncStats) -> None:
        """Updates UI with real-time statistics."""
        self.current_stats = stats

        # Update speed label
        self.speed_label.setText(f"{self._format_speed(stats.current_speed)}")

        # Update report dialog if open
        if self.report_dialog and self.report_dialog.isVisible():
            self.report_dialog.update_stats(stats)

    def _format_speed(self, speed: float) -> str:
        """Formats speed in bytes/sec to human readable string."""
        for unit in C.UNITS_SPEED:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} {C.UNIT_SPEED_TB}"

    def stop_synchronization(self) -> None:
        """Stops synchronization."""
        if self.sync_thread and self.sync_thread.isRunning():
            self.model.stop()
            self._set_action_buttons(sync=False, stop=False, cancel=False)
            self.status_label.setText(C.STATUS_STOPPING)

    def cancel_synchronization(self) -> None:
        """Cancels synchronization and rolls back changes."""
        if self.sync_thread and self.sync_thread.isRunning():
            self.cancel_requested = True
            self.model.stop()
            self._set_action_buttons(sync=False, stop=False, cancel=False)
            self.status_label.setText(C.STATUS_STOPPING_ROLLBACK)

    def on_cancel_finished(self, errors: list[str]) -> None:
        """Handler for rollback completion."""
        self._safe_cleanup_thread(self.cancel_thread)
        self.cancel_thread = None
        self.cancel_requested = False
        self._set_action_buttons(sync=True, stop=False, cancel=False)

        self.load_trees()

        if errors:
            error_message = C.MSG_ROLLBACK_ERRORS_HEADER + "\n".join(errors[:10])
            if len(errors) > 10:
                error_message += C.MSG_ROLLBACK_MORE_ERRORS.format(len(errors) - 10)

            QMessageBox.warning(self, C.DIALOG_ROLLBACK_ERRORS, error_message)

            failed_files = set()
            for error in errors:
                if C.ERR_FAILED_TO_DELETE in error:
                    file_path = error.split(C.ERR_FAILED_TO_DELETE)[1].split(":")[0].strip()
                    failed_files.add(Path(file_path))

            if failed_files and self.dir2_path:
                self.tree2.load_directory(self.dir2_path)
                self.tree2.set_highlight_group("failed", failed_files, C.COLOR_HIGHLIGHT_SYNC)

            self.status_label.setText(C.STATUS_ROLLBACK_WITH_ERRORS.format(len(errors)))
        else:
            self.status_label.setText(C.STATUS_CANCELLED_ROLLED_BACK)
            QMessageBox.information(self, C.DIALOG_CANCELLED, C.MSG_CANCELLED_SUCCESS)

    def on_sync_finished(self, result: dict[str, Any]) -> None:
        """Handler for synchronization completion."""
        self._safe_cleanup_thread(self.sync_thread)
        self.sync_thread = None
        self.speed_label.setText(C.STATUS_FINISHED)
        sync_stopped = result.get("error") == C.MSG_SYNC_STOPPED

        if self.cancel_requested:
            self.status_label.setText(C.STATUS_SYNC_STOPPED_ROLLBACK)
            self._start_cancel_thread()
            return

        self._set_action_buttons(sync=True, stop=False, cancel=False)

        if sync_stopped:
            QMessageBox.information(self, C.DIALOG_STOPPED, C.MSG_SYNC_STOPPED_USER)
            self.status_label.setText(C.STATUS_SYNC_STOPPED)
            return

        if "error" in result:
            QMessageBox.critical(self, C.DIALOG_ERROR, str(result["error"]))
            self.status_label.setText(f"{C.DIALOG_ERROR}: {result['error']}")
            return

        message = C.MSG_SYNC_COMPLETED_TEMPLATE.format(
            copied=result.get("copied", 0),
            replaced=result.get("replaced", 0),
            skipped=result.get("skipped", 0),
            unchanged=result.get("unchanged", 0),
        )

        if result.get("errors"):
            message += C.MSG_SYNC_ERRORS_HEADER + "\n".join(result["errors"][:10])

        QMessageBox.information(self, C.DIALOG_SYNC_COMPLETED, message)
        self.status_label.setText(C.STATUS_SYNC_COMPLETED)

        self.load_trees()
        if self.dir2_path:
            copied_files = set(result.get("copied_files") or set())
            replaced_files = set(result.get("replaced_files") or set())
            synced_files = copied_files | replaced_files
            if synced_files:
                self.tree2.load_directory(self.dir2_path)
                self.tree2.set_highlight_group("synced", synced_files, C.COLOR_HIGHLIGHT_SYNC)
                self.status_label.setText(C.STATUS_SYNC_COMPLETED_HIGHLIGHT)
            else:
                self.compare_directories()

    def update_status(self, message: str) -> None:
        """Updates status."""
        self.status_label.setText(message)
        QApplication.processEvents()

    def _on_file_double_clicked(self, file_path: Path) -> None:
        """Opens files in the OS default application when double-clicked."""
        try:
            self._open_file_with_default_app(file_path)
        except Exception as exc:
            QMessageBox.warning(
                self,
                C.DIALOG_OPEN_FILE_ERROR,
                C.MSG_OPEN_FILE_ERROR.format(file_path, exc),
            )

    def _open_file_with_default_app(self, file_path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(str(file_path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(file_path)], check=True)
        else:
            subprocess.run(["xdg-open", str(file_path)], check=True)

    def show_help(self) -> None:
        """Shows the help dialog."""
        dialog = HelpDialog(self)
        dialog.exec()

    def show_about(self) -> None:
        """Shows the about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def close_application(self) -> None:
        """Closes the app and releases resources."""
        self.model.stop()

        self._safe_cleanup_thread(self.sync_thread, 5000)
        self._safe_cleanup_thread(self.cancel_thread, 5000)
        self._safe_cleanup_thread(self.compare_thread, 5000)

        self.close()

    def load_trees(self) -> None:
        """Loads the directory trees."""
        if self.dir1_path:
            self.tree1.load_directory(self.dir1_path, compiled_rules=self.compiled_rules)
        if self.dir2_path:
            self.tree2.load_directory(self.dir2_path)

    def closeEvent(self, event) -> None:
        """Window close event handler."""
        self.close_application()
        event.accept()
