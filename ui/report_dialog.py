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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sync.interfaces import SyncStats
from ui.theme_manager import ThemeManager


class ReportDialog(QDialog):
    """
    Dialog for displaying synchronization report and live statistics.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Synchronization Report")
        self.setMinimumSize(800, 600)
        self.theme_manager = ThemeManager.instance()

        # Track processed items to avoid re-adding
        self._processed_count = 0

        self.setup_ui()
        self.theme_manager.register(self, role="dialog")
        self.apply_styles()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- Summary Section ---
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)

        # Left side: Progress
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel("Waiting to start...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)

        # Right side: Stats
        stats_layout = QVBoxLayout()
        self.time_label = QLabel("Time: 00:00")
        self.speed_label = QLabel("Speed: -")
        self.files_label = QLabel("Files: 0/0")
        self.bytes_label = QLabel("Data: 0 B / 0 B")

        stats_layout.addWidget(self.time_label)
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.files_label)
        stats_layout.addWidget(self.bytes_label)

        summary_layout.addLayout(progress_layout, stretch=2)
        summary_layout.addLayout(stats_layout, stretch=1)

        layout.addWidget(summary_widget)

        # --- Detailed Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Size", "Time"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # --- Footer ---
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_btn)

        layout.addLayout(footer_layout)

    def update_stats(self, stats: SyncStats) -> None:
        """Update the dialog with new statistics."""

        # Update progress
        if stats.total_files > 0:
            percent = int((stats.processed_files / stats.total_files) * 100)
            self.progress_bar.setValue(percent)

        self.progress_label.setText(f"Processing: {stats.processed_files}/{stats.total_files} files")

        # Update labels
        self.time_label.setText(f"Time: {self._format_time(stats.elapsed_time)}")
        self.speed_label.setText(f"Speed: {self._format_speed(stats.current_speed)}")
        self.files_label.setText(f"Files: {stats.processed_files}/{stats.total_files}")
        self.bytes_label.setText(
            f"Data: {self._format_bytes(stats.processed_bytes)} / {self._format_bytes(stats.total_bytes)}"
        )

        # Update table with new items
        new_items = stats.processed_items[self._processed_count :]
        if new_items:
            self.table.setUpdatesEnabled(False)
            for item in new_items:
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(str(item.relative_path)))

                status_item = QTableWidgetItem(item.status)
                if item.status == "error":
                    status_item.setForeground(Qt.GlobalColor.red)
                elif item.status == "skipped":
                    status_item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(row, 1, status_item)

                self.table.setItem(row, 2, QTableWidgetItem(self._format_bytes(item.size)))
                self.table.setItem(row, 3, QTableWidgetItem(self._format_timestamp(item.timestamp)))

                if item.error_message:
                    self.table.item(row, 0).setToolTip(item.error_message)

            self._processed_count += len(new_items)
            self.table.scrollToBottom()
            self.table.setUpdatesEnabled(True)

    def _format_bytes(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def _format_speed(self, speed: float) -> str:
        return f"{self._format_bytes(speed)}/s"

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _format_timestamp(self, timestamp: float) -> str:
        import datetime

        return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

    def apply_styles(self, theme: str | None = None) -> None:
        """Apply theme styles."""
        # This will be called by ThemeManager when theme changes
        # Basic styling logic here, or defer to main stylesheet if generic
        pass
