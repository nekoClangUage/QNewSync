"""
Tests for sync.interfaces module.
"""

from pathlib import Path

import pytest

from sync.interfaces import (
    DiffEntry,
    DiffResult,
    DirectorySnapshot,
    FileMeta,
    FileStatus,
    StrategyRegistry,
    SyncResult,
)


class TestFileMeta:
    """Tests for FileMeta dataclass."""

    def test_creation(self):
        meta = FileMeta(
            relative_path=Path("test.txt"),
            absolute_path=Path("/home/user/test.txt"),
            size=100,
            mtime=1234567890.0,
        )
        assert meta.relative_path == Path("test.txt")
        assert meta.size == 100
        assert meta.hash_value is None

    def test_with_hash(self):
        meta = FileMeta(
            relative_path=Path("test.txt"),
            absolute_path=Path("/home/user/test.txt"),
            size=100,
            mtime=1234567890.0,
        )
        new_meta = meta.with_hash("abc123")
        assert new_meta.hash_value == "abc123"
        assert meta.hash_value is None  # Original unchanged

    def test_immutability(self):
        meta = FileMeta(
            relative_path=Path("test.txt"),
            absolute_path=Path("/home/user/test.txt"),
            size=100,
            mtime=1234567890.0,
        )
        with pytest.raises(AttributeError):
            meta.size = 200


class TestDirectorySnapshot:
    """Tests for DirectorySnapshot dataclass."""

    def test_empty_snapshot(self):
        snapshot = DirectorySnapshot(base_path=Path("/test"))
        assert len(snapshot) == 0
        assert Path("test.txt") not in snapshot

    def test_with_files(self):
        files = {
            Path("a.txt"): FileMeta(Path("a.txt"), Path("/test/a.txt"), 10, 1.0),
            Path("b.txt"): FileMeta(Path("b.txt"), Path("/test/b.txt"), 20, 2.0),
        }
        snapshot = DirectorySnapshot(base_path=Path("/test"), files=files)
        assert len(snapshot) == 2
        assert Path("a.txt") in snapshot
        assert snapshot.get(Path("a.txt")).size == 10


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_empty_diff(self):
        diff = DiffResult(Path("/src"), Path("/dst"))
        assert len(diff.files_to_copy) == 0
        assert len(diff.files_to_replace) == 0

    def test_categorization(self):
        entries = {
            Path("new.txt"): DiffEntry(
                Path("new.txt"),
                FileStatus.TO_COPY,
                FileMeta(Path("new.txt"), Path("/src/new.txt"), 10, 1.0),
                None,
            ),
            Path("changed.txt"): DiffEntry(
                Path("changed.txt"),
                FileStatus.TO_REPLACE,
                FileMeta(Path("changed.txt"), Path("/src/changed.txt"), 20, 2.0),
                FileMeta(Path("changed.txt"), Path("/dst/changed.txt"), 15, 1.5),
            ),
            Path("only_dst.txt"): DiffEntry(
                Path("only_dst.txt"),
                FileStatus.ONLY_IN_TARGET,
                None,
                FileMeta(Path("only_dst.txt"), Path("/dst/only_dst.txt"), 30, 3.0),
            ),
            Path("same.txt"): DiffEntry(
                Path("same.txt"),
                FileStatus.UNCHANGED,
                FileMeta(Path("same.txt"), Path("/src/same.txt"), 40, 4.0),
                FileMeta(Path("same.txt"), Path("/dst/same.txt"), 40, 4.0),
            ),
        }
        diff = DiffResult(Path("/src"), Path("/dst"), entries)

        assert len(diff.files_to_copy) == 1
        assert Path("new.txt") in diff.files_to_copy

        assert len(diff.files_to_replace) == 1
        assert Path("changed.txt") in diff.files_to_replace

        assert len(diff.files_only_in_target) == 1
        assert Path("only_dst.txt") in diff.files_only_in_target

        assert len(diff.files_unchanged) == 1
        assert Path("same.txt") in diff.files_unchanged


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_to_dict(self):
        result = SyncResult(
            copied_count=5,
            replaced_count=3,
            skipped_count=2,
            unchanged_count=10,
            copied_files={Path("a.txt"), Path("b.txt")},
            replaced_files={Path("c.txt")},
            errors=["Error 1"],
        )
        d = result.to_dict()
        assert d["copied"] == 5
        assert d["replaced"] == 3
        assert d["skipped"] == 2
        assert d["unchanged"] == 10
        assert len(d["errors"]) == 1


class TestStrategyRegistry:
    """Tests for StrategyRegistry."""

    def test_register_and_get(self):
        registry = StrategyRegistry()
        registry.register("test", "value1")
        assert registry.get("test") == "value1"

    def test_default(self):
        registry = StrategyRegistry()
        registry.register("first", "value1", set_default=True)
        registry.register("second", "value2")
        assert registry.get_default() == "value1"
        assert registry.default_name == "first"

    def test_set_default(self):
        registry = StrategyRegistry()
        registry.register("first", "value1")
        registry.register("second", "value2")
        registry.set_default("second")
        assert registry.get_default() == "value2"

    def test_duplicate_registration_raises(self):
        registry = StrategyRegistry()
        registry.register("test", "value1")
        with pytest.raises(ValueError):
            registry.register("test", "value2")

    def test_unregister(self):
        registry = StrategyRegistry()
        registry.register("test", "value1")
        assert registry.unregister("test") is True
        assert registry.get("test") is None

    def test_list_names(self):
        registry = StrategyRegistry()
        registry.register("a", "1")
        registry.register("b", "2")
        names = registry.list_names()
        assert "a" in names
        assert "b" in names

    def test_contains(self):
        registry = StrategyRegistry()
        registry.register("test", "value")
        assert "test" in registry
        assert "other" not in registry

    def test_len(self):
        registry = StrategyRegistry()
        assert len(registry) == 0
        registry.register("a", "1")
        assert len(registry) == 1
