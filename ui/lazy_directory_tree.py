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
Lazy directory tree widget using QTreeView + QFileSystemModel.

This implementation provides a performant, lazy-loading directory tree
that doesn't block the UI when opening large directories. File highlighting
for diff results is handled via a proxy model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import (
    QDir,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QBrush, QColor, QFileSystemModel
from PyQt6.QtWidgets import QTreeView, QWidget

from app_settings import CompiledRegexRule, should_include_path


class HighlightProxyModel(QSortFilterProxyModel):
    """
    Proxy model that adds highlighting capabilities to QFileSystemModel.

    Paths to highlight are stored as normalized strings (forward slashes)
    relative to the base path. Different colors can be used for different
    highlight groups (e.g., files to copy vs files only in target).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_path: Path | None = None
        self._highlight_groups: dict[str, set[str]] = {}
        self._highlight_colors: dict[str, QColor] = {}
        self._background_alpha = 50
        self._compiled_rules: list[CompiledRegexRule] = []
        self._header_label: str | None = None

    def set_base_path(self, base_path: Path | None) -> None:
        """Set the base path for calculating relative paths."""
        self._base_path = base_path.resolve() if base_path else None

    def set_compiled_rules(self, rules: list[CompiledRegexRule]) -> None:
        """Set compiled regex rules for filtering files."""
        self._compiled_rules = list(rules or [])
        self.invalidateFilter()

    def set_highlight_group(
        self,
        group_name: str,
        paths: set[Path],
        color: QColor,
    ) -> None:
        """
        Set a highlight group with paths and color.

        Args:
            group_name: Unique identifier for this highlight group
            paths: Set of relative paths to highlight
            color: Color to use for highlighting
        """
        normalized = {str(p).replace("\\", "/") for p in paths}
        self._highlight_groups[group_name] = normalized
        self._highlight_colors[group_name] = color
        self.invalidate()

    def clear_highlights(self) -> None:
        """Clear all highlight groups."""
        self._highlight_groups.clear()
        self._highlight_colors.clear()
        self.invalidate()

    def remove_highlight_group(self, group_name: str) -> None:
        """Remove a specific highlight group."""
        self._highlight_groups.pop(group_name, None)
        self._highlight_colors.pop(group_name, None)
        self.invalidate()

    def _get_relative_path(self, index: QModelIndex) -> str | None:
        """Get the relative path for a model index."""
        if not self._base_path:
            return None

        source_model = self.sourceModel()
        if not isinstance(source_model, QFileSystemModel):
            return None

        source_index = self.mapToSource(index)
        file_path = source_model.filePath(source_index)
        if not file_path:
            return None

        try:
            path = Path(file_path).resolve()
            relative = path.relative_to(self._base_path)
            return str(relative).replace("\\", "/")
        except (ValueError, OSError):
            return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Override data to add highlighting."""
        if role == Qt.ItemDataRole.ForegroundRole:
            rel_path = self._get_relative_path(index)
            if rel_path:
                for group_name, paths in self._highlight_groups.items():
                    if rel_path in paths:
                        color = self._highlight_colors.get(group_name)
                        if color:
                            return QBrush(color)

        if role == Qt.ItemDataRole.BackgroundRole:
            rel_path = self._get_relative_path(index)
            if rel_path:
                for group_name, paths in self._highlight_groups.items():
                    if rel_path in paths:
                        color = self._highlight_colors.get(group_name)
                        if color:
                            bg_color = QColor(
                                color.red(),
                                color.green(),
                                color.blue(),
                                self._background_alpha,
                            )
                            return QBrush(bg_color)

        return super().data(index, role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Override to return custom header label if set."""
        if (
            self._header_label is not None
            and section == 0
            and orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self._header_label
        return super().headerData(section, orientation, role)

    def set_header_label(self, label: str) -> None:
        """Set a custom header label for column 0."""
        self._header_label = label
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 0)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Filter rows based on compiled regex rules."""
        if not self._compiled_rules:
            return True

        source_model = self.sourceModel()
        if not isinstance(source_model, QFileSystemModel):
            return True

        index = source_model.index(source_row, 0, source_parent)

        if source_model.isDir(index):
            return True

        if not self._base_path:
            return True

        file_path = source_model.filePath(index)
        if not file_path:
            return True

        try:
            path = Path(file_path).resolve()
            relative = path.relative_to(self._base_path)
            return should_include_path(relative, self._compiled_rules)
        except (ValueError, OSError):
            return True


class LazyDirectoryTreeWidget(QTreeView):
    """
    Tree view for displaying directory structure with lazy loading.

    Uses QFileSystemModel for efficient, on-demand loading of directory
    contents. Supports highlighting specific paths with custom colors.

    Signals:
        fileDoubleClicked: Emitted when a file is double-clicked (Path)
        directoryChanged: Emitted when the root directory changes (Path)
    """

    fileDoubleClicked = pyqtSignal(Path)
    directoryChanged = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._base_path: Path | None = None
        self._ignore_hidden = True

        self._file_model = QFileSystemModel(self)
        self._file_model.setReadOnly(True)

        self._proxy_model = HighlightProxyModel(self)
        self._proxy_model.setSourceModel(self._file_model)

        self.setHeaderHidden(False)
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        for col in range(1, 4):
            self.setColumnHidden(col, True)

        self.doubleClicked.connect(self._on_double_clicked)

        self._apply_filters()

    def set_ignore_hidden(self, ignore_hidden: bool) -> None:
        """Set whether to ignore hidden files/directories."""
        if self._ignore_hidden != ignore_hidden:
            self._ignore_hidden = ignore_hidden
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply file filters based on current settings."""
        filters = QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot

        if not self._ignore_hidden:
            filters |= QDir.Filter.Hidden

        self._file_model.setFilter(filters)

    def load_directory(
        self,
        directory_path: Path,
        highlight_files: set[Path] | None = None,
        highlight_color: QColor | None = None,
        compiled_rules: list[CompiledRegexRule] | None = None,
    ) -> None:
        """
        Load a directory into the tree view.

        Args:
            directory_path: Path to the directory to display
            highlight_files: Optional set of relative paths to highlight
            highlight_color: Color to use for highlighting
            compiled_rules: Optional compiled regex rules for filtering files
        """
        if not directory_path or not directory_path.exists():
            return

        self._base_path = directory_path.resolve()
        self._proxy_model.set_base_path(self._base_path)
        self._proxy_model.set_compiled_rules(compiled_rules or [])

        root_path = str(self._base_path)
        self._file_model.setRootPath(root_path)

        if self.model() is None:
            self.setModel(self._proxy_model)
            self.setColumnWidth(0, 200)   # Name — wider
            self.setColumnWidth(1, 80)    # Size
            self.setColumnWidth(2, 80)    # Type — smaller

        source_index = self._file_model.index(root_path)
        proxy_index = self._proxy_model.mapFromSource(source_index)
        self.setRootIndex(proxy_index)

        self._proxy_model.clear_highlights()
        if highlight_files and highlight_color:
            self._proxy_model.set_highlight_group(
                "default",
                highlight_files,
                highlight_color,
            )

        self.directoryChanged.emit(self._base_path)

    def set_highlight_group(
        self,
        group_name: str,
        paths: set[Path],
        color: QColor,
    ) -> None:
        """Add or update a highlight group."""
        self._proxy_model.set_highlight_group(group_name, paths, color)
        self.viewport().update()

    def clear_highlights(self) -> None:
        """Clear all highlighting."""
        self._proxy_model.clear_highlights()
        self.viewport().update()

    def remove_highlight_group(self, group_name: str) -> None:
        """Remove a specific highlight group."""
        self._proxy_model.remove_highlight_group(group_name)
        self.viewport().update()

    def resolve_item_path(self, index: QModelIndex) -> Path | None:
        """Get the absolute path for a model index."""
        source_index = self._proxy_model.mapToSource(index)
        file_path = self._file_model.filePath(source_index)
        if file_path:
            return Path(file_path)
        return None

    def get_relative_path(self, index: QModelIndex) -> Path | None:
        """Get the relative path for a model index."""
        if not self._base_path:
            return None

        abs_path = self.resolve_item_path(index)
        if not abs_path:
            return None

        try:
            return abs_path.relative_to(self._base_path)
        except ValueError:
            return None

    def is_file(self, index: QModelIndex) -> bool:
        """Check if the index represents a file (not directory)."""
        source_index = self._proxy_model.mapToSource(index)
        return not self._file_model.isDir(source_index)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """Handle double-click on an item."""
        if self.is_file(index):
            path = self.resolve_item_path(index)
            if path:
                self.fileDoubleClicked.emit(path)

    @property
    def base_path(self) -> Path | None:
        """Get the current base path."""
        return self._base_path

    def set_header_label(self, label: str) -> None:
        """Set the header label for the name column."""
        self._proxy_model.set_header_label(label)

    def set_header_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Set default text alignment for the header view."""
        self.header().setDefaultAlignment(alignment)

    def clear(self) -> None:
        """Clear the tree view — returns to empty startup state."""
        self._proxy_model.clear_highlights()
        self._base_path = None
        self.setModel(None)
