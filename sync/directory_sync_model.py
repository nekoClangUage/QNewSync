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
Directory synchronization model.

This module provides the core logic for comparing and synchronizing directories,
coordinating the various strategies (scanning, hashing, diffing, execution).
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from app_settings import CompiledRegexRule, should_include_path
from sync.bootstrap import ensure_strategies_registered
from sync.interfaces import (
    DiffStrategy,
    DirectoryScanner,
    DirectorySnapshot,
    FileMeta,
    HashProvider,
    ProgressCallback,
    StatsCallback,
    SyncExecutor,
    SyncResult,
    diff_strategy_registry,
    hash_provider_registry,
    scanner_registry,
    sync_executor_registry,
)


class DiffMode:
    """Available diff modes for directory comparison."""

    STRICT = "strict"  # Full hash comparison (most accurate, slowest)
    TWO_PHASE = "two-phase"  # Size/mtime first, then hash if needed (balanced)
    FAST = "fast"  # Size/mtime only (fastest, less accurate)


class DirectorySyncModel:
    """
    Model for directory synchronization.

    This model supports pluggable strategies for scanning, hashing, and diffing.
    It acts as a facade, coordinating the workflow from scan to sync.
    """

    def __init__(self) -> None:
        ensure_strategies_registered()
        self.dir1_path: Path | None = None
        self.dir2_path: Path | None = None
        self.stop_event = threading.Event()
        self.progress_callback: ProgressCallback | None = None
        self.stats_callback: StatsCallback | None = None
        self.backup_dir: Path | None = None
        self.copied_files: set[Path] = set()
        self.replaced_files: set[Path] = set()
        self.replaced_files_backup: dict[Path, Path] = {}
        self.planned_copies: set[Path] = set()
        self.planned_replacements: set[Path] = set()
        self.dir2_existing_dirs: set[Path] = set()
        self.ignore_hidden = True
        self.copy_empty_dirs = False
        self.compiled_rules: list[CompiledRegexRule] = []

        # Strategy-based configuration
        self._diff_mode: str = DiffMode.TWO_PHASE
        self._scanner: DirectoryScanner | None = None
        self._hash_provider: HashProvider | None = None
        self._diff_strategy: DiffStrategy | None = None
        self._sync_executor: SyncExecutor | None = None

        # Cached snapshots for optimization
        self._dir1_snapshot: DirectorySnapshot | None = None
        self._dir2_snapshot: DirectorySnapshot | None = None

    def set_filters(
        self,
        *,
        ignore_hidden: bool,
        copy_empty_dirs: bool,
        compiled_rules: list[CompiledRegexRule] | None = None,
    ) -> None:
        """Set file filtering rules."""
        self.ignore_hidden = ignore_hidden
        self.copy_empty_dirs = copy_empty_dirs
        self.compiled_rules = list(compiled_rules or [])
        # Invalidate cached snapshots when filters change
        self._dir1_snapshot = None
        self._dir2_snapshot = None

    def set_diff_mode(self, mode: str) -> None:
        """Set the diff mode (strict, two-phase, or fast)."""
        valid_modes = {DiffMode.STRICT, DiffMode.TWO_PHASE, DiffMode.FAST}
        if mode not in valid_modes:
            raise ValueError(f"Invalid diff mode: {mode}. Must be one of {valid_modes}")
        self._diff_mode = mode
        self._diff_strategy = None  # Reset to pick up new mode

    def get_diff_mode(self) -> str:
        """Get the current diff mode."""
        return self._diff_mode

    def _get_scanner(self) -> DirectoryScanner:
        """Get the directory scanner (lazily initialized)."""
        if self._scanner is None:
            self._scanner = scanner_registry.get_default()
        return self._scanner

    def _get_hash_provider(self) -> HashProvider:
        """Get the hash provider (lazily initialized)."""
        if self._hash_provider is None:
            self._hash_provider = hash_provider_registry.get_default()
        return self._hash_provider

    def _get_diff_strategy(self) -> DiffStrategy:
        """Get the diff strategy based on current mode (lazily initialized)."""
        if self._diff_strategy is None:
            self._diff_strategy = diff_strategy_registry.get(self._diff_mode)
        return self._diff_strategy

    def _get_sync_executor(self) -> SyncExecutor:
        """Get the sync executor (lazily initialized)."""
        if self._sync_executor is None:
            self._sync_executor = sync_executor_registry.get_default()
        return self._sync_executor

    def _apply_dir1_rules(self, snapshot: DirectorySnapshot) -> DirectorySnapshot:
        """Apply regex filtering rules to the source directory snapshot."""
        if not self.compiled_rules:
            return snapshot

        filtered_files: dict[Path, FileMeta] = {}
        for rel_path, meta in snapshot.files.items():
            if should_include_path(rel_path, self.compiled_rules):
                filtered_files[rel_path] = meta

        filtered_dirs: set[Path] = set()
        for rel_path in snapshot.directories:
            if should_include_path(rel_path, self.compiled_rules):
                filtered_dirs.add(rel_path)

        return DirectorySnapshot(
            base_path=snapshot.base_path,
            files=filtered_files,
            directories=filtered_dirs,
            scan_time=snapshot.scan_time,
        )

    def set_directories(self, dir1: str, dir2: str) -> None:
        """Sets directory paths and validates them."""
        new_dir1 = Path(dir1).resolve()
        new_dir2 = Path(dir2).resolve()

        # Invalidate cached snapshots when directories change
        if new_dir1 != self.dir1_path or new_dir2 != self.dir2_path:
            self._dir1_snapshot = None
            self._dir2_snapshot = None

        self.dir1_path = new_dir1
        self.dir2_path = new_dir2

        # Validate that one directory is not inside the other
        try:
            if self.dir2_path.is_relative_to(self.dir1_path):
                raise ValueError(
                    f"Directory 2 cannot be inside directory 1!\n"
                    f"Directory 1: {self.dir1_path}\n"
                    f"Directory 2: {self.dir2_path}"
                )
            if self.dir1_path.is_relative_to(self.dir2_path):
                raise ValueError(
                    f"Directory 1 cannot be inside directory 2!\n"
                    f"Directory 1: {self.dir1_path}\n"
                    f"Directory 2: {self.dir2_path}"
                )
        except AttributeError:
            # Fallback for older Python versions if is_relative_to is missing (should not happen on 3.10+)
            try:
                common_path = Path(os.path.commonpath([self.dir1_path, self.dir2_path]))
            except ValueError:
                common_path = None

            if common_path == self.dir1_path:
                raise ValueError(
                    f"Directory 2 cannot be inside directory 1!\n"
                    f"Directory 1: {self.dir1_path}\n"
                    f"Directory 2: {self.dir2_path}"
                ) from None
            if common_path == self.dir2_path:
                raise ValueError(
                    f"Directory 1 cannot be inside directory 2!\n"
                    f"Directory 1: {self.dir1_path}\n"
                    f"Directory 2: {self.dir2_path}"
                ) from None

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Sets a callback for progress updates."""
        self.progress_callback = callback

    def set_stats_callback(self, callback: StatsCallback | None) -> None:
        """Sets a callback for statistics updates."""
        self.stats_callback = callback

    def stop(self) -> None:
        """Stops synchronization."""
        self.stop_event.set()

    def reset_stop(self) -> None:
        """Clears the stop flag."""
        self.stop_event.clear()

    def _collect_directories(self, base_path: Path) -> set[Path]:
        """Collects all directories under a base path (relative paths only)."""
        directories: set[Path] = set()
        if not base_path.exists():
            return directories

        for root, dirs, _ in os.walk(base_path):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    directories.add(dir_path.relative_to(base_path))
                except ValueError:
                    continue

        return directories

    def compare_directories(self) -> tuple[dict[Path, str], dict[Path, str], set[Path], set[Path]]:
        """
        Compares two directories.

        Returns:
            tuple: (files_to_copy, files_to_replace, files_only_in_target, files_unchanged)
        """
        if not self.dir1_path or not self.dir2_path:
            return {}, {}, set(), set()

        if not self.dir1_path.exists():
            return {}, {}, set(), set()

        if self._dir1_snapshot is None:
            self._dir1_snapshot = self._get_scanner().scan(
                self.dir1_path,
                exclude_path=self.dir2_path,
                ignore_hidden=self.ignore_hidden,
                stop_event=self.stop_event,
                progress_callback=self.progress_callback,
            )

        if self._dir2_snapshot is None:
            self._dir2_snapshot = self._get_scanner().scan(
                self.dir2_path,
                exclude_path=self.dir1_path,
                ignore_hidden=self.ignore_hidden,
                stop_event=self.stop_event,
                progress_callback=self.progress_callback,
            )

        source_snapshot = self._apply_dir1_rules(self._dir1_snapshot)
        target_snapshot = self._dir2_snapshot

        diff = self._get_diff_strategy().compare(
            source_snapshot,
            target_snapshot,
            self._get_hash_provider(),
            stop_event=self.stop_event,
            progress_callback=self.progress_callback,
        )

        files_to_copy = {path: (meta.hash_value or "") for path, meta in diff.files_to_copy.items()}
        files_to_replace = {path: (meta.hash_value or "") for path, meta in diff.files_to_replace.items()}

        return files_to_copy, files_to_replace, diff.files_only_in_target, diff.files_unchanged

    def synchronize(self) -> dict[str, Any]:
        """Synchronizes directory 2 with directory 1."""
        self.reset_stop()
        self.planned_copies = set()
        self.planned_replacements = set()
        self.dir2_existing_dirs = set()

        if not self.dir1_path or not self.dir2_path:
            return {"error": "Directories are not set"}

        if not self.dir1_path.exists():
            return {"error": f"Directory 1 does not exist: {self.dir1_path}"}

        self.dir2_path.mkdir(parents=True, exist_ok=True)

        if self.progress_callback:
            self.progress_callback("Comparing directories...")

        # Perform comparison if needed or reuse cached snapshots
        # Note: We re-scan if we want to be absolutely sure of latest state,
        # but for performance we often rely on what compare_directories generated.
        # However, to ensure correctness during sync, we do a fresh scan/compare here
        # implicitly by calling compare() which uses snapshots.
        # If we want to force refresh, we should clear snapshots.
        # For now, we assume snapshots are fresh enough or cleared by UI if needed.

        # We need strict/fresh comparison for sync?
        # Ideally yes. But let's use the standard flow.

        # Refresh snapshots for sync to avoid stale data
        self._dir1_snapshot = None
        self._dir2_snapshot = None

        # We duplicate the logic from compare_directories but inline it to ensure
        # we have the DiffResult object which contains everything we need.
        diff = self._get_diff_strategy().compare(
            self._apply_dir1_rules(
                self._get_scanner().scan(
                    self.dir1_path,
                    exclude_path=self.dir2_path,
                    ignore_hidden=self.ignore_hidden,
                    stop_event=self.stop_event,
                    progress_callback=self.progress_callback,
                )
            ),
            self._get_scanner().scan(
                self.dir2_path,
                exclude_path=self.dir1_path,
                ignore_hidden=self.ignore_hidden,
                stop_event=self.stop_event,
                progress_callback=self.progress_callback,
            ),
            self._get_hash_provider(),
            stop_event=self.stop_event,
            progress_callback=self.progress_callback,
        )

        if self.stop_event.is_set():
            return {"error": "Synchronization stopped"}

        self.planned_copies = set(diff.files_to_copy.keys())
        self.planned_replacements = set(diff.files_to_replace.keys())
        self.dir2_existing_dirs = self._collect_directories(self.dir2_path)

        has_files_to_sync = bool(diff.files_to_copy or diff.files_to_replace)
        has_dirs_to_sync = bool(diff.directories_to_create) and self.copy_empty_dirs

        if not has_files_to_sync and not has_dirs_to_sync:
            return SyncResult(
                skipped_count=len(diff.files_only_in_target),
                unchanged_count=len(diff.files_unchanged),
            ).to_dict()

        if diff.files_to_replace:
            self.create_backup_dir()

        result = self._get_sync_executor().execute(
            diff,
            backup_dir=self.backup_dir,
            copy_empty_dirs=self.copy_empty_dirs,
            stop_event=self.stop_event,
            progress_callback=self.progress_callback,
            stats_callback=self.stats_callback,
        )

        self.copied_files = result.copied_files
        self.replaced_files = result.replaced_files

        return result.to_dict()

    def rollback_changes(self) -> list[str]:
        """Rollback all changes made during synchronization."""
        errors: list[str] = []

        if self.progress_callback:
            self.progress_callback("Rolling back changes...")

        errors.extend(
            self._get_sync_executor().rollback(
                stop_event=self.stop_event,
                progress_callback=self.progress_callback,
            )
        )

        # Remove empty directories that were created during sync
        if self.dir2_path and self.dir2_path.exists():
            for root, dirs, _ in os.walk(self.dir2_path, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    if dir_path == self.dir2_path:
                        continue
                    try:
                        rel_path = dir_path.relative_to(self.dir2_path)
                    except ValueError:
                        continue
                    if rel_path in self.dir2_existing_dirs:
                        continue
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except (OSError, PermissionError):
                        continue

        # Reset tracking
        self.copied_files = set()
        self.replaced_files = set()
        self.replaced_files_backup = {}
        self.planned_copies = set()
        self.planned_replacements = set()
        self.dir2_existing_dirs = set()
        self.backup_dir = None

        return errors

    def create_backup_dir(self) -> Path:
        """Create a temporary backup directory."""
        if not self.backup_dir:
            self.backup_dir = Path(tempfile.mkdtemp(prefix="sync_backup_"))
        return self.backup_dir
