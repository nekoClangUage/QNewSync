"""
Tests for sync.strategies module.
"""

from pathlib import Path

from sync.interfaces import (
    DirectorySnapshot,
    FileMeta,
    diff_strategy_registry,
    hash_provider_registry,
    scanner_registry,
)
from sync.strategies import (
    CachingHashProvider,
    DefaultDirectoryScanner,
    DefaultHashProvider,
    FastDiffStrategy,
)


class TestDefaultDirectoryScanner:
    """Tests for DefaultDirectoryScanner."""

    def test_scan_empty_directory(self, tmp_path):
        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(tmp_path)
        assert len(snapshot) == 0
        assert snapshot.base_path == tmp_path.resolve()

    def test_scan_with_files(self, tmp_path):
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(tmp_path)

        assert len(snapshot) == 2
        assert Path("file1.txt") in snapshot
        assert Path("file2.txt") in snapshot

    def test_scan_with_subdirectories(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")
        (tmp_path / "root.txt").write_text("root")

        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(tmp_path)

        assert len(snapshot) == 2
        assert Path("root.txt") in snapshot
        assert Path("subdir/nested.txt") in snapshot or Path("subdir\\nested.txt") in snapshot

    def test_scan_ignores_hidden(self, tmp_path):
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / "visible.txt").write_text("visible")

        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(tmp_path, ignore_hidden=True)

        assert len(snapshot) == 1
        assert Path("visible.txt") in snapshot

    def test_scan_includes_hidden(self, tmp_path):
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / "visible.txt").write_text("visible")

        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(tmp_path, ignore_hidden=False)

        assert len(snapshot) == 2

    def test_scan_nonexistent_directory(self):
        scanner = DefaultDirectoryScanner()
        snapshot = scanner.scan(Path("/nonexistent/path"))
        assert len(snapshot) == 0


class TestDefaultHashProvider:
    """Tests for DefaultHashProvider."""

    def test_calculate_hash(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        provider = DefaultHashProvider()
        hash_value = provider.calculate_hash(test_file)

        assert hash_value is not None
        assert len(hash_value) == 32  # MD5 hex length

    def test_calculate_hash_same_content(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("same content")
        file2.write_text("same content")

        provider = DefaultHashProvider()
        hash1 = provider.calculate_hash(file1)
        hash2 = provider.calculate_hash(file2)

        assert hash1 == hash2

    def test_calculate_hash_different_content(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content A")
        file2.write_text("content B")

        provider = DefaultHashProvider()
        hash1 = provider.calculate_hash(file1)
        hash2 = provider.calculate_hash(file2)

        assert hash1 != hash2

    def test_calculate_hash_nonexistent(self):
        provider = DefaultHashProvider()
        hash_value = provider.calculate_hash(Path("/nonexistent/file.txt"))
        assert hash_value is None


class TestCachingHashProvider:
    """Tests for CachingHashProvider."""

    def test_caching(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        stat = test_file.stat()

        provider = CachingHashProvider()

        # First call - should compute
        files = {Path("test.txt"): FileMeta(Path("test.txt"), test_file, stat.st_size, stat.st_mtime)}
        result1 = provider.calculate_hashes(files)
        assert provider.cache_size() == 1

        # Second call - should use cache
        result2 = provider.calculate_hashes(files)
        assert result1 == result2

    def test_cache_invalidation_on_change(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("content v1")
        stat1 = test_file.stat()

        provider = CachingHashProvider()

        files1 = {Path("test.txt"): FileMeta(Path("test.txt"), test_file, stat1.st_size, stat1.st_mtime)}
        result1 = provider.calculate_hashes(files1)

        # Modify file
        test_file.write_text("content v2 - different")
        stat2 = test_file.stat()

        files2 = {Path("test.txt"): FileMeta(Path("test.txt"), test_file, stat2.st_size, stat2.st_mtime)}
        result2 = provider.calculate_hashes(files2)

        # Should have different hashes
        assert result1[Path("test.txt")] != result2[Path("test.txt")]

    def test_clear_cache(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        stat = test_file.stat()

        provider = CachingHashProvider()
        files = {Path("test.txt"): FileMeta(Path("test.txt"), test_file, stat.st_size, stat.st_mtime)}
        provider.calculate_hashes(files)
        assert provider.cache_size() > 0

        provider.clear_cache()
        assert provider.cache_size() == 0


class TestDiffStrategies:
    """Tests for diff strategies."""

    def create_snapshot(self, base_path: Path, files: dict) -> DirectorySnapshot:
        """Helper to create a snapshot from a dict of path -> (size, mtime, hash)."""
        file_metas = {}
        for rel_path, (size, mtime, hash_val) in files.items():
            meta = FileMeta(
                relative_path=rel_path,
                absolute_path=base_path / rel_path,
                size=size,
                mtime=mtime,
                hash_value=hash_val,
            )
            file_metas[rel_path] = meta
        return DirectorySnapshot(base_path=base_path, files=file_metas)

    def test_fast_diff_detects_new_file(self, tmp_path):
        source = self.create_snapshot(
            tmp_path / "src",
            {Path("new.txt"): (100, 1.0, None)},
        )
        target = self.create_snapshot(tmp_path / "dst", {})

        strategy = FastDiffStrategy()
        provider = DefaultHashProvider()
        result = strategy.compare(source, target, provider)

        assert Path("new.txt") in result.files_to_copy

    def test_fast_diff_detects_size_change(self, tmp_path):
        source = self.create_snapshot(
            tmp_path / "src",
            {Path("file.txt"): (200, 2.0, None)},
        )
        target = self.create_snapshot(
            tmp_path / "dst",
            {Path("file.txt"): (100, 1.0, None)},
        )

        strategy = FastDiffStrategy()
        provider = DefaultHashProvider()
        result = strategy.compare(source, target, provider)

        assert Path("file.txt") in result.files_to_replace

    def test_fast_diff_unchanged(self, tmp_path):
        source = self.create_snapshot(
            tmp_path / "src",
            {Path("file.txt"): (100, 1.0, None)},
        )
        target = self.create_snapshot(
            tmp_path / "dst",
            {Path("file.txt"): (100, 1.0, None)},
        )

        strategy = FastDiffStrategy()
        provider = DefaultHashProvider()
        result = strategy.compare(source, target, provider)

        assert Path("file.txt") in result.files_unchanged


class TestRegistries:
    """Tests for strategy registries."""

    def test_scanner_registry_has_default(self):
        assert scanner_registry.get_default() is not None

    def test_hash_provider_registry_has_cached(self):
        assert "cached" in hash_provider_registry
        assert hash_provider_registry.get("cached") is not None

    def test_diff_strategy_registry_has_modes(self):
        assert "strict" in diff_strategy_registry
        assert "two-phase" in diff_strategy_registry
        assert "fast" in diff_strategy_registry
