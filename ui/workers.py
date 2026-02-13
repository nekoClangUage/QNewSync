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

from PyQt6.QtCore import QThread, pyqtSignal

from sync.directory_sync_model import DirectorySyncModel
from sync.interfaces import SyncStats


class CompareWorkerThread(QThread):
    """Worker thread that compares directories in the background."""

    finished = pyqtSignal(tuple)
    progress = pyqtSignal(str)

    def __init__(self, model: DirectorySyncModel) -> None:
        super().__init__()
        self.model = model
        self._progress_callback = None

    def _progress_handler(self, message: str) -> None:
        """Progress handler that emits a Qt signal."""
        self.progress.emit(message)

    def run(self) -> None:
        """Runs directory comparison."""
        try:
            original_callback = self.model.progress_callback
            self.model.set_progress_callback(self._progress_handler)

            result = self.model.compare_directories()

            self.model.set_progress_callback(original_callback)

            self.finished.emit(result)
        except Exception:
            self.finished.emit(({}, {}, set(), set()))


class SyncWorkerThread(QThread):
    """Worker thread that performs synchronization in the background."""

    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    stats_updated = pyqtSignal(object)  # SyncStats object

    def __init__(self, model: DirectorySyncModel) -> None:
        super().__init__()
        self.model = model

    def _stats_handler(self, stats: SyncStats) -> None:
        """Handler for statistics updates."""
        self.stats_updated.emit(stats)

    def run(self) -> None:
        """Runs synchronization."""
        try:
            # Connect stats callback
            self.model.set_stats_callback(self._stats_handler)

            result = self.model.synchronize()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e)})
        finally:
            # Cleanup callback
            self.model.set_stats_callback(None)


class CancelWorkerThread(QThread):
    """Worker thread that performs rollback in the background."""

    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, model: DirectorySyncModel) -> None:
        super().__init__()
        self.model = model

    def _progress_handler(self, message: str) -> None:
        """Progress handler that emits a Qt signal."""
        self.progress.emit(message)

    def run(self) -> None:
        """Runs rollback operation."""
        try:
            original_callback = self.model.progress_callback
            self.model.set_progress_callback(self._progress_handler)

            self.model.reset_stop()
            errors = self.model.rollback_changes()

            self.model.set_progress_callback(original_callback)

            self.finished.emit(errors)
        except Exception as e:
            self.finished.emit([f"Rollback error: {e!s}"])
