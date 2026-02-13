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
Default strategy implementations for the synchronization system.

These implementations wrap the existing functionality to maintain backward
compatibility while conforming to the new interface contracts.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
import threading
import time
from multiprocessing import Manager, Pool
from pathlib import Path
from typing import Any

from sync.interfaces import (
    DiffEntry,
    DiffResult,
    DirectorySnapshot,
    FileMeta,
    FileStatus,
    HashProvider,
    ProgressCallback,
    StatsCallback,
    StopEvent,
    SyncItem,
    SyncResult,
    SyncStats,
    diff_strategy_registry,
    hash_provider_registry,
    scanner_registry,
    sync_executor_registry,
)

# Type aliases for worker communication
HashWorkerArgs = tuple[Path, Path]
HashWorkerResult = tuple[Path, str | None]

CopyWorkerArgs = tuple[Path, Path, Path, bool, str | None, Any]
CopyWorkerResult = tuple[Path, bool, bool, str | None]

# =============================================================================
# Default Directory Scanner
# =============================================================================


class DefaultDirectoryScanner:
    """Default directory scanner using os.scandir for efficiency."""

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
        files: dict[Path, FileMeta] = {}
        directories: set[Path] = set()

        if not directory.exists():
            return DirectorySnapshot(
                base_path=directory,
                files=files,
                directories=directories,
                scan_time=0.0
            )

        directory_resolved = directory.resolve()
        exclude_resolved = exclude_path.resolve() if exclude_path and exclude_path.exists() else None

        start_time = time.time()

        def should_exclude(path: Path) -> bool:
            if exclude_resolved is None:
                return False
            try:
                resolved = path.resolve()
                if resolved == exclude_resolved:
                    return True
                try:
                    resolved.relative_to(exclude_resolved)
                    return True
                except ValueError:
                    pass
                try:
                    exclude_resolved.relative_to(resolved)
                    return True
                except ValueError:
                    pass
            except (ValueError, OSError):
                pass
            return False

        def scan_dir(current_path: Path) -> None:
            if stop_event and stop_event.is_set():
                return

            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        if stop_event and stop_event.is_set():
                            return

                        if ignore_hidden and entry.name.startswith("."):
                            continue

                        entry_path = Path(entry.path)

                        if should_exclude(entry_path):
                            continue

                        try:
                            if entry.is_dir(follow_symlinks=False):
                                relative_path = entry_path.relative_to(directory_resolved)
                                directories.add(relative_path)
                                scan_dir(entry_path)
                            elif entry.is_file(follow_symlinks=False):
                                stat_info = entry.stat(follow_symlinks=False)
                                relative_path = entry_path.relative_to(directory_resolved)
                                files[relative_path] = FileMeta(
                                    relative_path=relative_path,
                                    absolute_path=entry_path,
                                    size=stat_info.st_size,
                                    mtime=stat_info.st_mtime,
                                )
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                pass

        scan_dir(directory_resolved)
        scan_time = time.time() - start_time

        if progress_callback:
            progress_callback(f"Scanned {len(files)} files in {scan_time:.2f}s")

        return DirectorySnapshot(
            base_path=directory_resolved,
            files=files,
            directories=directories,
            scan_time=scan_time,
        )


# =============================================================================
# Default Hash Provider
# =============================================================================


class DefaultHashProvider:
    """Default hash provider using MD5 with parallel processing."""

    def __init__(self, chunk_size: int = 8192, num_workers: int | None = None):
        self._chunk_size = chunk_size
        self._num_workers = num_workers or (os.cpu_count() or 4)

    def calculate_hash(self, file_path: Path) -> str | None:
        """Calculate MD5 hash for a single file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(self._chunk_size):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except OSError:
            return None

    def calculate_hashes(
        self,
        files: dict[Path, FileMeta],
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[Path, str]:
        """Calculate hashes for multiple files using multiprocessing."""
        if not files:
            return {}

        args_list = [(meta.absolute_path, meta.relative_path) for meta in files.values()]

        hash_dict: dict[Path, str] = {}

        pool = None
        try:
            pool = Pool(processes=self._num_workers)
            results = pool.imap_unordered(
                _hash_worker,
                args_list,
                chunksize=max(1, len(args_list) // (self._num_workers * 4)),
            )

            processed = 0
            total = len(args_list)

            for relative_path, hash_value in results:
                if stop_event and stop_event.is_set():
                    pool.terminate()
                    pool.join()
                    pool = None
                    break

                processed += 1
                if hash_value:
                    hash_dict[relative_path] = hash_value

                if progress_callback and processed % 100 == 0:
                    progress_callback(f"Hashed {processed}/{total} files...")

        except Exception:
            for meta in files.values():
                if stop_event and stop_event.is_set():
                    break
                hash_value = self.calculate_hash(meta.absolute_path)
                if hash_value:
                    hash_dict[meta.relative_path] = hash_value
        finally:
            if pool is not None:
                pool.terminate()
                pool.join()

        return hash_dict


def _hash_worker(args: tuple) -> tuple:
    """Worker function for parallel hash calculation."""
    absolute_path, relative_path = args
    hash_md5 = hashlib.md5()
    try:
        with open(absolute_path, "rb") as f:
            while chunk := f.read(8192):
                hash_md5.update(chunk)
        return (relative_path, hash_md5.hexdigest())
    except OSError:
        return (relative_path, None)


# =============================================================================
# Caching Hash Provider
# =============================================================================


class CachingHashProvider:
    """
    Hash provider with in-memory caching based on path + size + mtime.

    Caches hash values and reuses them if the file's size and mtime
    haven't changed. This significantly speeds up repeated comparisons.
    """

    def __init__(
        self,
        base_provider: HashProvider | None = None,
        max_cache_size: int = 100000,
    ):
        self._base_provider = base_provider or DefaultHashProvider()
        self._max_cache_size = max_cache_size
        self._cache: dict[tuple, str] = {}
        self._lock = threading.RLock()

    def _cache_key(self, file_path: Path, size: int, mtime: float) -> tuple:
        """Generate a cache key from path, size, and mtime."""
        return (str(file_path), size, mtime)

    def get_cached(self, file_path: Path, size: int, mtime: float) -> str | None:
        """Get a cached hash if available."""
        key = self._cache_key(file_path, size, mtime)
        with self._lock:
            return self._cache.get(key)

    def put_cached(self, file_path: Path, size: int, mtime: float, hash_value: str) -> None:
        """Store a hash in the cache."""
        key = self._cache_key(file_path, size, mtime)
        with self._lock:
            if len(self._cache) >= self._max_cache_size:
                oldest_keys = list(self._cache.keys())[: len(self._cache) // 4]
                for old_key in oldest_keys:
                    self._cache.pop(old_key, None)
            self._cache[key] = hash_value

    def clear_cache(self) -> None:
        """Clear the hash cache."""
        with self._lock:
            self._cache.clear()

    def cache_size(self) -> int:
        """Get the current cache size."""
        with self._lock:
            return len(self._cache)

    def calculate_hash(self, file_path: Path) -> str | None:
        """Calculate hash for a single file (no caching for single-file calls)."""
        return self._base_provider.calculate_hash(file_path)

    def calculate_hashes(
        self,
        files: dict[Path, FileMeta],
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[Path, str]:
        """Calculate hashes with caching support."""
        if not files:
            return {}

        result: dict[Path, str] = {}
        to_hash: dict[Path, FileMeta] = {}

        for rel_path, meta in files.items():
            cached = self.get_cached(meta.absolute_path, meta.size, meta.mtime)
            if cached:
                result[rel_path] = cached
            else:
                to_hash[rel_path] = meta

        if progress_callback and result:
            progress_callback(f"Found {len(result)} cached hashes, computing {len(to_hash)} new...")

        if to_hash:
            new_hashes = self._base_provider.calculate_hashes(
                to_hash,
                stop_event=stop_event,
                progress_callback=progress_callback,
            )

            for rel_path, hash_value in new_hashes.items():
                if hash_value:
                    result[rel_path] = hash_value
                    meta = to_hash[rel_path]
                    self.put_cached(meta.absolute_path, meta.size, meta.mtime, hash_value)

        return result


# =============================================================================
# Default Diff Strategies
# =============================================================================


class FullHashDiffStrategy:
    """
    Diff strategy that always uses full hash comparison.
    Most accurate but slowest.
    """

    def compare(
        self,
        source: DirectorySnapshot,
        target: DirectorySnapshot,
        hash_provider: HashProvider,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DiffResult:
        """Compare using full hash for all files."""
        entries: dict[Path, DiffEntry] = {}

        if progress_callback:
            progress_callback("Calculating hashes for source directory...")

        source_hashes = hash_provider.calculate_hashes(
            source.files,
            stop_event=stop_event,
            progress_callback=progress_callback,
        )

        if stop_event and stop_event.is_set():
            return DiffResult(source.base_path, target.base_path, entries)

        if progress_callback:
            progress_callback("Calculating hashes for target directory...")

        target_hashes = hash_provider.calculate_hashes(
            target.files,
            stop_event=stop_event,
            progress_callback=progress_callback,
        )

        if stop_event and stop_event.is_set():
            return DiffResult(source.base_path, target.base_path, entries)

        all_paths = set(source.files.keys()) | set(target.files.keys())

        for path in all_paths:
            source_meta = source.get(path)
            target_meta = target.get(path)
            source_hash = source_hashes.get(path)
            target_hash = target_hashes.get(path)

            if source_meta and not target_meta:
                status = FileStatus.TO_COPY
            elif not source_meta and target_meta:
                status = FileStatus.ONLY_IN_TARGET
            elif source_hash and target_hash and source_hash != target_hash:
                status = FileStatus.TO_REPLACE
            else:
                status = FileStatus.UNCHANGED

            if source_meta and source_hash:
                source_meta = source_meta.with_hash(source_hash)
            if target_meta and target_hash:
                target_meta = target_meta.with_hash(target_hash)

            entries[path] = DiffEntry(
                relative_path=path,
                status=status,
                source_meta=source_meta,
                target_meta=target_meta,
            )

        directories_to_create = source.directories - target.directories

        return DiffResult(source.base_path, target.base_path, entries, directories_to_create)


class TwoPhaseDiffStrategy:
    """
    Two-phase diff strategy: first compare size/mtime, then hash only when needed.
    Much faster for directories with many unchanged files.
    """

    def compare(
        self,
        source: DirectorySnapshot,
        target: DirectorySnapshot,
        hash_provider: HashProvider,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DiffResult:
        """Compare using two-phase approach: size/mtime first, then hash."""
        entries: dict[Path, DiffEntry] = {}
        needs_hash: dict[Path, FileMeta] = {}

        all_paths = set(source.files.keys()) | set(target.files.keys())

        for path in all_paths:
            if stop_event and stop_event.is_set():
                return DiffResult(source.base_path, target.base_path, entries, set())

            source_meta = source.get(path)
            target_meta = target.get(path)

            if source_meta and not target_meta:
                entries[path] = DiffEntry(path, FileStatus.TO_COPY, source_meta, None)
            elif not source_meta and target_meta:
                entries[path] = DiffEntry(path, FileStatus.ONLY_IN_TARGET, None, target_meta)
            elif source_meta and target_meta:
                if source_meta.size != target_meta.size:
                    entries[path] = DiffEntry(path, FileStatus.TO_REPLACE, source_meta, target_meta)
                elif source_meta.mtime != target_meta.mtime:
                    needs_hash[path] = source_meta
                else:
                    entries[path] = DiffEntry(path, FileStatus.UNCHANGED, source_meta, target_meta)

        if needs_hash and not (stop_event and stop_event.is_set()):
            if progress_callback:
                progress_callback(f"Hashing {len(needs_hash)} files that may have changed...")

            source_subset = {p: source.files[p] for p in needs_hash}
            target_subset = {p: target.files[p] for p in needs_hash if p in target.files}

            source_hashes = hash_provider.calculate_hashes(
                source_subset, stop_event=stop_event, progress_callback=progress_callback
            )
            target_hashes = hash_provider.calculate_hashes(
                target_subset, stop_event=stop_event, progress_callback=progress_callback
            )

            for path in needs_hash:
                source_hash = source_hashes.get(path)
                target_hash = target_hashes.get(path)
                source_meta = source.get(path)
                target_meta = target.get(path)

                if source_hash:
                    source_meta = source_meta.with_hash(source_hash)
                if target_hash:
                    target_meta = target_meta.with_hash(target_hash)

                if source_hash and target_hash and source_hash != target_hash:
                    status = FileStatus.TO_REPLACE
                else:
                    status = FileStatus.UNCHANGED

                entries[path] = DiffEntry(path, status, source_meta, target_meta)

        directories_to_create = source.directories - target.directories

        return DiffResult(source.base_path, target.base_path, entries, directories_to_create)


class FastDiffStrategy:
    """
    Fast diff strategy using only size/mtime comparison.
    Fastest but may miss content changes if mtime is unreliable.
    """

    def compare(
        self,
        source: DirectorySnapshot,
        target: DirectorySnapshot,
        hash_provider: HashProvider,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DiffResult:
        """Compare using only size and mtime (no hashing)."""
        entries: dict[Path, DiffEntry] = {}

        all_paths = set(source.files.keys()) | set(target.files.keys())

        for path in all_paths:
            if stop_event and stop_event.is_set():
                break

            source_meta = source.get(path)
            target_meta = target.get(path)

            if source_meta and not target_meta:
                status = FileStatus.TO_COPY
            elif not source_meta and target_meta:
                status = FileStatus.ONLY_IN_TARGET
            elif source_meta and target_meta:
                if source_meta.size != target_meta.size or source_meta.mtime > target_meta.mtime:
                    status = FileStatus.TO_REPLACE
                else:
                    status = FileStatus.UNCHANGED
            else:
                status = FileStatus.UNCHANGED

            entries[path] = DiffEntry(path, status, source_meta, target_meta)

        directories_to_create = source.directories - target.directories

        return DiffResult(source.base_path, target.base_path, entries, directories_to_create)


# =============================================================================
# Default Sync Executor
# =============================================================================

_MAX_PROCESSED_ITEMS = 500
_STATS_THROTTLE_INTERVAL_MS = 100
_ROLLBACK_RETRIES = 5
_ROLLBACK_RETRY_DELAY = 0.3


class DefaultSyncExecutor:
    """Default sync executor with backup and rollback support."""

    def __init__(self, num_workers: int | None = None, debug_logging: bool = False):
        self._num_workers = num_workers or (os.cpu_count() or 4)
        self._debug_logging = debug_logging
        self._backup_dir: Path | None = None
        self._copied_files: set[Path] = set()
        self._replaced_files: set[Path] = set()
        self._replaced_files_backup: dict[Path, Path] = {}
        self._target_path: Path | None = None
        self._created_dirs: set[Path] = set()

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
        logger = None
        if self._debug_logging:
            logging.basicConfig(
                filename="sync_debug.log", level=logging.DEBUG, format="%(asctime)s %(message)s", force=True
            )
            logger = logging.getLogger("sync_executor")
            logger.info("Starting execution...")

        self._target_path = diff.target_path
        self._copied_files = set()
        self._replaced_files = set()
        self._replaced_files_backup = {}
        self._created_dirs = set()

        # Store planned operations for robust rollback
        self._planned_copies = set(diff.files_to_copy.keys())
        self._planned_replacements = set(diff.files_to_replace.keys())

        files_to_copy = diff.files_to_copy
        files_to_replace = diff.files_to_replace
        directories_to_create = diff.directories_to_create if copy_empty_dirs else set()

        if not files_to_copy and not files_to_replace and not directories_to_create:
            return SyncResult(
                skipped_count=len(diff.files_only_in_target),
                unchanged_count=len(diff.files_unchanged),
            )

        # Initialize stats
        total_files = len(files_to_copy) + len(files_to_replace) + len(directories_to_create)
        total_bytes = sum(m.size for m in files_to_copy.values()) + sum(m.size for m in files_to_replace.values())

        start_time = time.time()
        stats = SyncStats(total_files=total_files, total_bytes=total_bytes, start_time=start_time)

        if files_to_replace:
            if backup_dir:
                self._backup_dir = backup_dir
            else:
                self._backup_dir = Path(tempfile.mkdtemp(prefix="sync_backup_"))

        diff.target_path.mkdir(parents=True, exist_ok=True)

        # Handle empty directories first
        if directories_to_create:
            if progress_callback:
                progress_callback(f"Creating {len(directories_to_create)} directories...")

            for rel_path in sorted(directories_to_create):
                if stop_event and stop_event.is_set():
                    break

                target_dir = diff.target_path / rel_path
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self._created_dirs.add(rel_path)

                    # Update stats for directory creation
                    stats.processed_files += 1
                    stats.processed_items.append(SyncItem(
                        relative_path=rel_path,
                        status="created_dir",
                        size=0,
                        timestamp=time.time()
                    ))
                    if stats_callback:
                        stats_callback(stats)

                except Exception as e:
                    if logger:
                        logger.error(f"Failed to create directory {rel_path}: {e}")

        all_files = {**files_to_copy, **files_to_replace}

        copied_count = 0
        replaced_count = 0
        errors: list[str] = []
        pool = None
        manager = None

        try:
            if all_files:
                manager = Manager()
            if all_files:
                mp_stop = manager.Event()

                if stop_event and stop_event.is_set():
                    mp_stop.set()

                args_list = []
                for path, meta in all_files.items():
                    is_replace = path in files_to_replace
                    args_list.append(
                        (
                            meta.absolute_path,
                            diff.target_path / path,
                            path,
                            is_replace,
                            str(self._backup_dir) if self._backup_dir else None,
                            mp_stop,
                        )
                    )

                pool = Pool(processes=self._num_workers)
                results = pool.imap_unordered(
                    _copy_worker,
                    args_list,
                    chunksize=max(1, len(args_list) // (self._num_workers * 4)),
                )

                processed = 0
                total = len(args_list)
                stopping = False

                # Map for quick lookup of file sizes to update stats
                file_sizes = {p: m.size for p, m in all_files.items()}

                for rel_path, success, is_replace, error_msg in results:
                    if not stopping and stop_event and stop_event.is_set():
                        mp_stop.set()
                        stopping = True
                        break

                    processed += 1

                    # Update stats
                    current_time = time.time()
                    elapsed = current_time - start_time
                    file_size = file_sizes.get(rel_path, 0)

                    stats.processed_files += 1
                    if success:
                        stats.processed_bytes += file_size

                    stats.elapsed_time = elapsed
                    if elapsed > 0:
                        stats.current_speed = stats.processed_bytes / elapsed

                    status_str = "error"
                    if success:
                        status_str = "replaced" if is_replace else "copied"
                    elif error_msg == "Stopped":
                        status_str = "skipped"

                    item = SyncItem(
                        relative_path=rel_path,
                        status=status_str,
                        size=file_size,
                        timestamp=current_time,
                        error_message=error_msg if not success else None,
                    )
                    stats.processed_items.append(item)
                    if len(stats.processed_items) > _MAX_PROCESSED_ITEMS:
                        stats.processed_items = stats.processed_items[-_MAX_PROCESSED_ITEMS:]

                    if stats_callback:
                        now_ms = current_time * 1000
                        if not hasattr(self, "_last_stats_time"):
                            self._last_stats_time = 0.0
                        if (now_ms - self._last_stats_time) >= _STATS_THROTTLE_INTERVAL_MS or processed >= total:
                            self._last_stats_time = now_ms
                            stats_callback(stats)

                    if success:
                        if is_replace:
                            replaced_count += 1
                            self._replaced_files.add(rel_path)
                        else:
                            copied_count += 1
                            self._copied_files.add(rel_path)
                    elif error_msg and error_msg != "Stopped":
                        errors.append(f"{rel_path}: {error_msg}")

                    if progress_callback:
                        if stopping:
                            progress_callback(f"Stopping… tracked {processed}/{total} files")
                        else:
                            progress_callback(f"Processed {processed}/{total} files...")

        except Exception as e:
            errors.append(f"Sync error: {e!s}")
        finally:
            # 1. Signal workers to stop (redundant but safe)
            if manager is not None:
                try:
                    mp_stop.set()
                except Exception:
                    pass

            # 2. Terminate pool
            if pool is not None:
                try:
                    pool.terminate()
                    pool.join()
                except Exception:
                    pass

            # 3. Shutdown manager
            if manager is not None:
                try:
                    manager.shutdown()
                except Exception:
                    pass

        return SyncResult(
            copied_count=copied_count,
            replaced_count=replaced_count,
            skipped_count=len(diff.files_only_in_target),
            unchanged_count=len(diff.files_unchanged),
            copied_files=self._copied_files,
            replaced_files=self._replaced_files,
            created_directories=self._created_dirs,
            errors=errors,
        )

    def rollback(
        self,
        *,
        stop_event: StopEvent | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[str]:
        """Rollback changes made during the last execution."""
        logger = None
        if self._debug_logging:
            logger = logging.getLogger("sync_executor")

        errors: list[str] = []

        if progress_callback:
            progress_callback("Rolling back changes...")

        if logger:
            logger.info("Starting rollback...")

        try:
            # Robust cleanup: include planned copies that might have been copied but not tracked
            # due to an interruption (Stop).
            files_to_cleanup = self._copied_files.copy()
            if hasattr(self, "_planned_copies") and self._planned_copies:
                if logger:
                    logger.info(f"Including {len(self._planned_copies)} planned copies in rollback cleanup.")
                files_to_cleanup.update(self._planned_copies)

            total_files = len(files_to_cleanup)
            processed_files = 0

            for rel_path in files_to_cleanup:
                if stop_event and stop_event.is_set():
                    if logger:
                        logger.info("Rollback stopped by event.")
                    break
                target_path = self._target_path / rel_path
                if not target_path.exists():
                    processed_files += 1
                    if progress_callback and processed_files % 10 == 0:
                        progress_callback(f"Rolling back... {processed_files}/{total_files}")
                    continue
                deleted = False
                last_error = None
                for attempt in range(_ROLLBACK_RETRIES):
                    try:
                        target_path.unlink()
                        deleted = True
                        if logger:
                            logger.debug(f"Deleted {rel_path}")
                        break
                    except PermissionError as e:
                        last_error = e
                        if attempt < _ROLLBACK_RETRIES - 1:
                            time.sleep(_ROLLBACK_RETRY_DELAY)
                    except Exception as e:
                        last_error = e
                        break
                if not deleted and last_error is not None:
                    msg = f"Failed to delete {rel_path}: {last_error!s}"
                    errors.append(msg)
                    if logger:
                        logger.error(msg)

                processed_files += 1
                if progress_callback and processed_files % 10 == 0:
                    progress_callback(f"Rolling back... {processed_files}/{total_files}")

            if self._backup_dir and self._backup_dir.exists():
                if logger:
                    logger.info(f"Restoring backups from {self._backup_dir}...")
                for root, _, files in os.walk(self._backup_dir):
                    for file in files:
                        if stop_event and stop_event.is_set():
                            break
                        backup_path = Path(root) / file
                        try:
                            rel_path = backup_path.relative_to(self._backup_dir)
                            target_path = self._target_path / rel_path
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup_path, target_path)
                            if logger:
                                logger.debug(f"Restored {rel_path}")
                        except Exception as e:
                            msg = f"Failed to restore {rel_path}: {e!s}"
                            errors.append(msg)
                            if logger:
                                logger.error(msg)

                try:
                    shutil.rmtree(self._backup_dir)
                except Exception as e:
                    if logger:
                        logger.error(f"Failed to remove backup dir: {e}")
        except Exception as e:
            msg = f"Critical error during rollback: {e}"
            errors.append(msg)
            if logger:
                logger.error(msg)
        finally:
            self._copied_files = set()
            self._replaced_files = set()
            self._replaced_files_backup = {}
            self._backup_dir = None

            # Rollback created directories
            if self._created_dirs:
                if logger:
                    logger.info(f"Rolling back {len(self._created_dirs)} created directories...")
                # Sort in reverse order to delete nested directories first
                for rel_path in sorted(self._created_dirs, reverse=True):
                    try:
                        dir_path = self._target_path / rel_path
                        if dir_path.exists() and not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            if logger:
                                logger.debug(f"Removed created directory {rel_path}")
                    except Exception as e:
                        if logger:
                            logger.error(f"Failed to remove created directory {rel_path}: {e}")
                self._created_dirs = set()

            if logger:
                logger.info("Rollback finished.")

        return errors


def _copy_worker(args: tuple) -> tuple:
    """Worker function for parallel file copying."""
    source_path, target_path, rel_path, is_replace, backup_dir_str, mp_stop = args

    try:
        if mp_stop and mp_stop.is_set():
            return (rel_path, False, is_replace, "Stopped")

        if is_replace and target_path.exists() and backup_dir_str:
            backup_path = Path(backup_dir_str) / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_path)

        if mp_stop and mp_stop.is_set():
            return (rel_path, False, is_replace, "Stopped")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        return (rel_path, True, is_replace, None)
    except Exception as e:
        return (rel_path, False, is_replace, str(e))


# =============================================================================
# Register Default Strategies
# =============================================================================


def register_default_strategies() -> None:
    """Register all default strategy implementations."""
    if "default" not in scanner_registry:
        scanner_registry.register("default", DefaultDirectoryScanner(), set_default=True)

    if "default" not in hash_provider_registry:
        hash_provider_registry.register("default", DefaultHashProvider())
    if "cached" not in hash_provider_registry:
        hash_provider_registry.register("cached", CachingHashProvider(), set_default=True)

    if "strict" not in diff_strategy_registry:
        diff_strategy_registry.register("strict", FullHashDiffStrategy(), set_default=True)
    if "two-phase" not in diff_strategy_registry:
        diff_strategy_registry.register("two-phase", TwoPhaseDiffStrategy())
    if "fast" not in diff_strategy_registry:
        diff_strategy_registry.register("fast", FastDiffStrategy())

    if "default" not in sync_executor_registry:
        sync_executor_registry.register("default", DefaultSyncExecutor(), set_default=True)
