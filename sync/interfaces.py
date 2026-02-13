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
Core interfaces and domain models for the synchronization system.

This module defines the contracts (protocols) that allow extensibility
without modifying existing implementations. New strategies can be registered
and swapped at runtime.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

# =============================================================================
# Domain Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class FileMeta:
    """Immutable metadata for a single file."""

    relative_path: Path
    absolute_path: Path
    size: int
    mtime: float
    hash_value: str | None = None

    def with_hash(self, hash_value: str) -> FileMeta:
        """Return a new FileMeta with the hash populated."""
        return FileMeta(
            relative_path=self.relative_path,
            absolute_path=self.absolute_path,
            size=self.size,
            mtime=self.mtime,
            hash_value=hash_value,
        )


@dataclass(frozen=True, slots=True)
class DirectorySnapshot:
    """Immutable snapshot of a directory's file structure."""

    base_path: Path
    files: dict[Path, FileMeta] = field(default_factory=dict)
    directories: set[Path] = field(default_factory=set)
    scan_time: float = 0.0

    def __len__(self) -> int:
        return len(self.files)

    def __contains__(self, relative_path: Path) -> bool:
        return relative_path in self.files

    def get(self, relative_path: Path) -> FileMeta | None:
        return self.files.get(relative_path)


class FileStatus(Enum):
    """Status of a file in the diff result."""

    TO_COPY = auto()  # exists only in source
    TO_REPLACE = auto()  # exists in both, content differs
    ONLY_IN_TARGET = auto()  # exists only in target
    UNCHANGED = auto()  # exists in both, content matches


@dataclass(frozen=True, slots=True)
class DiffEntry:
    """A single entry in the diff result."""

    relative_path: Path
    status: FileStatus
    source_meta: FileMeta | None = None
    target_meta: FileMeta | None = None


@dataclass
class DiffResult:
    """Result of comparing two directory snapshots."""

    source_path: Path
    target_path: Path
    entries: dict[Path, DiffEntry] = field(default_factory=dict)
    directories_to_create: set[Path] = field(default_factory=set)

    @property
    def files_to_copy(self) -> dict[Path, FileMeta]:
        return {
            path: entry.source_meta
            for path, entry in self.entries.items()
            if entry.status == FileStatus.TO_COPY and entry.source_meta
        }

    @property
    def files_to_replace(self) -> dict[Path, FileMeta]:
        return {
            path: entry.source_meta
            for path, entry in self.entries.items()
            if entry.status == FileStatus.TO_REPLACE and entry.source_meta
        }

    @property
    def files_only_in_target(self) -> set[Path]:
        return {path for path, entry in self.entries.items() if entry.status == FileStatus.ONLY_IN_TARGET}

    @property
    def files_unchanged(self) -> set[Path]:
        return {path for path, entry in self.entries.items() if entry.status == FileStatus.UNCHANGED}


@dataclass
class SyncResult:
    """Result of a synchronization operation."""

    copied_count: int = 0
    replaced_count: int = 0
    skipped_count: int = 0
    unchanged_count: int = 0
    copied_files: set[Path] = field(default_factory=set)
    replaced_files: set[Path] = field(default_factory=set)
    created_directories: set[Path] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return {
            "copied": self.copied_count,
            "replaced": self.replaced_count,
            "skipped": self.skipped_count,
            "unchanged": self.unchanged_count,
            "copied_files": self.copied_files,
            "replaced_files": self.replaced_files,
            "created_directories": self.created_directories,
            "errors": self.errors,
        }


@dataclass(frozen=True, slots=True)
class SyncItem:
    """Represents a single item processed during synchronization."""

    relative_path: Path
    status: str  # "copied", "replaced", "skipped", "error"
    size: int
    timestamp: float
    error_message: str | None = None


@dataclass
class SyncStats:
    """Real-time synchronization statistics."""

    total_files: int = 0
    processed_files: int = 0
    total_bytes: int = 0
    processed_bytes: int = 0
    start_time: float = 0.0
    elapsed_time: float = 0.0
    current_speed: float = 0.0  # bytes per second
    processed_items: list[SyncItem] = field(default_factory=list)


# =============================================================================
# Protocols (Interfaces)
# =============================================================================

ProgressCallback = Callable[[str], None]
StatsCallback = Callable[[SyncStats], None]
StopEvent = threading.Event


@runtime_checkable
class DirectoryScanner(Protocol):
    """Protocol for directory scanning strategies."""

    def scan(
        self,
        directory: Path,
        *,
        exclude_path: Path | None = None,
        ignore_hidden: bool = True,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DirectorySnapshot:
        """Scan a directory and return a snapshot of its contents."""
        ...


@runtime_checkable
class HashProvider(Protocol):
    """Protocol for hash calculation strategies."""

    def calculate_hash(self, file_path: Path) -> str | None:
        """Calculate hash for a single file."""
        ...

    def calculate_hashes(
        self,
        files: dict[Path, FileMeta],
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[Path, str]:
        """Calculate hashes for multiple files. Returns mapping of relative_path -> hash."""
        ...


@runtime_checkable
class DiffStrategy(Protocol):
    """Protocol for directory comparison strategies."""

    def compare(
        self,
        source: DirectorySnapshot,
        target: DirectorySnapshot,
        hash_provider: HashProvider,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DiffResult:
        """Compare two directory snapshots and return the diff."""
        ...


@runtime_checkable
class SyncExecutor(Protocol):
    """Protocol for synchronization execution strategies."""

    def execute(
        self,
        diff: DiffResult,
        *,
        backup_dir: Path | None = None,
        copy_empty_dirs: bool = False,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
        stats_callback: StatsCallback | None = None,
    ) -> SyncResult:
        """Execute the synchronization based on the diff result."""
        ...

    def rollback(
        self,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[str]:
        """Rollback changes made during the last execution. Returns list of errors."""
        ...


# =============================================================================
# Strategy Registry
# =============================================================================

T = TypeVar("T")


class StrategyRegistry(Generic[T]):
    """
    Generic registry for managing and retrieving strategy implementations.

    Thread-safe registry that allows registering, retrieving, and listing
    strategy implementations by name.
    """

    def __init__(self, default_name: str | None = None) -> None:
        self._strategies: dict[str, T] = {}
        self._default_name: str | None = default_name
        self._lock = threading.RLock()

    def register(self, name: str, strategy: T, *, set_default: bool = False) -> None:
        """Register a strategy with the given name."""
        with self._lock:
            if name in self._strategies:
                raise ValueError(f"Strategy '{name}' is already registered")
            self._strategies[name] = strategy
            if set_default or self._default_name is None:
                self._default_name = name

    def unregister(self, name: str) -> bool:
        """Unregister a strategy by name. Returns True if removed."""
        with self._lock:
            if name in self._strategies:
                del self._strategies[name]
                if self._default_name == name:
                    self._default_name = next(iter(self._strategies), None)
                return True
            return False

    def get(self, name: str | None = None) -> T | None:
        """Get a strategy by name, or the default if name is None."""
        with self._lock:
            target_name = name if name is not None else self._default_name
            if target_name is None:
                return None
            return self._strategies.get(target_name)

    def get_default(self) -> T | None:
        """Get the default strategy."""
        return self.get(None)

    def set_default(self, name: str) -> None:
        """Set the default strategy by name."""
        with self._lock:
            if name not in self._strategies:
                raise ValueError(f"Strategy '{name}' is not registered")
            self._default_name = name

    @property
    def default_name(self) -> str | None:
        """Get the name of the default strategy."""
        with self._lock:
            return self._default_name

    def list_names(self) -> list[str]:
        """List all registered strategy names."""
        with self._lock:
            return list(self._strategies.keys())

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._strategies

    def __len__(self) -> int:
        with self._lock:
            return len(self._strategies)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._strategies.keys()))


# =============================================================================
# Global Registries
# =============================================================================

scanner_registry: StrategyRegistry[DirectoryScanner] = StrategyRegistry()
hash_provider_registry: StrategyRegistry[HashProvider] = StrategyRegistry()
diff_strategy_registry: StrategyRegistry[DiffStrategy] = StrategyRegistry()
sync_executor_registry: StrategyRegistry[SyncExecutor] = StrategyRegistry()
