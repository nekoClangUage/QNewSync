"""
Tests for DefaultSyncExecutor: error handling, debug logging, stats throttling.
"""

from pathlib import Path

from sync.interfaces import (
    DiffEntry,
    DiffResult,
    FileMeta,
    FileStatus,
    SyncStats,
)
from sync.strategies import _MAX_PROCESSED_ITEMS, DefaultSyncExecutor


def _make_diff(tmp_path, files_to_copy=None, files_to_replace=None):
    """Helper to build a DiffResult from simple dicts."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(exist_ok=True)
    dst.mkdir(exist_ok=True)

    entries = {}
    for rel, content in (files_to_copy or {}).items():
        abs_path = src / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        meta = FileMeta(rel, abs_path, len(content), abs_path.stat().st_mtime)
        entries[rel] = DiffEntry(rel, FileStatus.TO_COPY, source_meta=meta)

    for rel, (src_content, dst_content) in (files_to_replace or {}).items():
        abs_src = src / rel
        abs_dst = dst / rel
        abs_src.parent.mkdir(parents=True, exist_ok=True)
        abs_dst.parent.mkdir(parents=True, exist_ok=True)
        abs_src.write_text(src_content, encoding="utf-8")
        abs_dst.write_text(dst_content, encoding="utf-8")
        meta = FileMeta(rel, abs_src, len(src_content), abs_src.stat().st_mtime)
        entries[rel] = DiffEntry(rel, FileStatus.TO_REPLACE, source_meta=meta)

    return DiffResult(source_path=src, target_path=dst, entries=entries)


# =============================================================================
# Debug logging gating
# =============================================================================


class TestDebugLogging:
    def test_logging_disabled_by_default(self, tmp_path):
        """With debug_logging=False (default), no sync_debug.log should be created in cwd."""
        executor = DefaultSyncExecutor()
        assert executor._debug_logging is False

    def test_logging_enabled(self, tmp_path):
        executor = DefaultSyncExecutor(debug_logging=True)
        assert executor._debug_logging is True


# =============================================================================
# Stats throttling and capping
# =============================================================================


class TestStatsThrottling:
    def test_processed_items_capped(self, tmp_path):
        """processed_items should not grow beyond _MAX_PROCESSED_ITEMS."""
        # Create enough files to exceed the cap
        num_files = _MAX_PROCESSED_ITEMS + 100
        files_to_copy = {}
        for i in range(num_files):
            files_to_copy[Path(f"file_{i}.txt")] = f"content_{i}"

        diff = _make_diff(tmp_path, files_to_copy=files_to_copy)

        last_stats = [None]

        def stats_cb(stats: SyncStats):
            last_stats[0] = stats

        executor = DefaultSyncExecutor(num_workers=2)
        executor.execute(diff, stats_callback=stats_cb)

        assert last_stats[0] is not None
        assert len(last_stats[0].processed_items) <= _MAX_PROCESSED_ITEMS

    def test_stats_callback_receives_updates(self, tmp_path):
        """Stats callback should be called at least once."""
        files_to_copy = {Path("a.txt"): "aaa", Path("b.txt"): "bbb"}
        diff = _make_diff(tmp_path, files_to_copy=files_to_copy)

        call_count = [0]

        def stats_cb(stats: SyncStats):
            call_count[0] += 1

        executor = DefaultSyncExecutor(num_workers=1)
        executor.execute(diff, stats_callback=stats_cb)

        assert call_count[0] >= 1


# =============================================================================
# Copy error handling
# =============================================================================


class TestExecutorErrors:
    def test_copy_nonexistent_source(self, tmp_path):
        """Copying from a nonexistent source should produce an error, not crash."""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        # Create a DiffResult that references a file that doesn't exist
        ghost = Path("ghost.txt")
        meta = FileMeta(ghost, src / ghost, 10, 0.0)
        entries = {ghost: DiffEntry(ghost, FileStatus.TO_COPY, source_meta=meta)}
        diff = DiffResult(source_path=src, target_path=dst, entries=entries)

        executor = DefaultSyncExecutor(num_workers=1)
        result = executor.execute(diff)

        assert result.copied_count == 0
        assert len(result.errors) >= 1

    def test_execute_empty_diff(self, tmp_path):
        """Empty diff should return zero counts and no errors."""
        diff = _make_diff(tmp_path)
        executor = DefaultSyncExecutor()
        result = executor.execute(diff)

        assert result.copied_count == 0
        assert result.replaced_count == 0
        assert result.errors == []


# =============================================================================
# Rollback
# =============================================================================


class TestExecutorRollback:
    def test_rollback_after_copy(self, tmp_path):
        """Rollback should remove copied files."""
        files_to_copy = {Path("new.txt"): "new content"}
        diff = _make_diff(tmp_path, files_to_copy=files_to_copy)
        dst = diff.target_path

        executor = DefaultSyncExecutor(num_workers=1)
        result = executor.execute(diff)
        assert result.copied_count == 1
        assert (dst / "new.txt").exists()

        errors = executor.rollback()
        assert errors == []
        assert not (dst / "new.txt").exists()

    def test_rollback_after_replace_restores_original(self, tmp_path):
        """Rollback should restore replaced files from backup."""
        files_to_replace = {Path("file.txt"): ("new version", "original version")}
        diff = _make_diff(tmp_path, files_to_replace=files_to_replace)
        dst = diff.target_path

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        executor = DefaultSyncExecutor(num_workers=1)
        result = executor.execute(diff, backup_dir=backup_dir)
        assert result.replaced_count == 1
        assert (dst / "file.txt").read_text(encoding="utf-8") == "new version"

        errors = executor.rollback()
        assert errors == []
        assert (dst / "file.txt").read_text(encoding="utf-8") == "original version"
