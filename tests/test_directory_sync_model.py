from pathlib import Path

import pytest

from sync.directory_sync_model import DirectorySyncModel


def test_directory_sync_model_synchronize_copies_and_replaces(temp_dir, sync_model):
    dir1 = temp_dir["dir1"]
    dir2 = temp_dir["dir2"]
    write_file = temp_dir["write_file"]

    write_file(dir1, Path("new.txt"), "new")
    write_file(dir1, Path("same.txt"), "same")
    write_file(dir1, Path("changed.txt"), "dir1")

    write_file(dir2, Path("same.txt"), "same")
    write_file(dir2, Path("changed.txt"), "dir2")
    write_file(dir2, Path("only_dir2.txt"), "only")

    sync_model.set_directories(str(dir1), str(dir2))
    sync_model.set_diff_mode("strict")  # Use strict mode to ensure content changes are detected
    result = sync_model.synchronize()

    assert result["copied"] == 1
    assert result["replaced"] == 1
    assert result["skipped"] == 1
    assert result["unchanged"] == 1
    assert result["errors"] == []

    assert result["copied_files"] == {Path("new.txt")}
    assert result["replaced_files"] == {Path("changed.txt")}

    assert (dir2 / "new.txt").read_text(encoding="utf-8") == "new"
    assert (dir2 / "changed.txt").read_text(encoding="utf-8") == "dir1"

    sync_model.rollback_changes()


# =============================================================================
# Nested directory validation
# =============================================================================


def test_set_directories_rejects_nested_dir(tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = dir1 / "dir2"
    dir2.mkdir(parents=True)

    model = DirectorySyncModel()
    with pytest.raises(ValueError, match="Directory 2 cannot be inside directory 1"):
        model.set_directories(str(dir1), str(dir2))


def test_set_directories_rejects_dir1_inside_dir2(tmp_path):
    """Symmetric check: dir1 inside dir2 should also be rejected."""
    dir2 = tmp_path / "outer"
    dir1 = dir2 / "inner"
    dir1.mkdir(parents=True)

    model = DirectorySyncModel()
    with pytest.raises(ValueError, match="Directory 1 cannot be inside directory 2"):
        model.set_directories(str(dir1), str(dir2))


def test_set_directories_accepts_siblings(tmp_path):
    dir1 = tmp_path / "dir_a"
    dir2 = tmp_path / "dir_b"
    dir1.mkdir()
    dir2.mkdir()

    model = DirectorySyncModel()
    model.set_directories(str(dir1), str(dir2))
    assert model.dir1_path == dir1.resolve()
    assert model.dir2_path == dir2.resolve()


# =============================================================================
# Snapshot cache invalidation
# =============================================================================


def test_set_directories_invalidates_snapshot_cache(tmp_path):
    """Changing directories should clear cached snapshots."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir3 = tmp_path / "dir3"
    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()

    (dir1 / "a.txt").write_text("a")
    (dir3 / "b.txt").write_text("b")

    model = DirectorySyncModel()
    model.set_directories(str(dir1), str(dir2))

    # Trigger comparison to populate snapshot cache
    files_to_copy, _, _, _ = model.compare_directories()
    assert Path("a.txt") in files_to_copy

    # Change dir1 → dir3; cached snapshots should be invalidated
    model.set_directories(str(dir3), str(dir2))
    files_to_copy2, _, _, _ = model.compare_directories()
    assert Path("b.txt") in files_to_copy2
    assert Path("a.txt") not in files_to_copy2


def test_set_directories_same_dirs_keeps_cache(tmp_path):
    """Setting the same directories again should NOT invalidate cache."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "file.txt").write_text("content")

    model = DirectorySyncModel()
    model.set_directories(str(dir1), str(dir2))
    model.compare_directories()

    # Snapshots should be populated
    assert model._dir1_snapshot is not None
    assert model._dir2_snapshot is not None

    # Setting same dirs again should keep cache
    model.set_directories(str(dir1), str(dir2))
    assert model._dir1_snapshot is not None
    assert model._dir2_snapshot is not None


def test_set_filters_invalidates_snapshot_cache(tmp_path):
    """Changing filters should clear cached snapshots."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "file.txt").write_text("content")

    model = DirectorySyncModel()
    model.set_directories(str(dir1), str(dir2))
    model.compare_directories()

    assert model._dir1_snapshot is not None

    model.set_filters(ignore_hidden=False, copy_empty_dirs=False)
    assert model._dir1_snapshot is None
    assert model._dir2_snapshot is None


# =============================================================================
# Diff mode
# =============================================================================


def test_set_diff_mode_valid():
    model = DirectorySyncModel()
    for mode in ("strict", "two-phase", "fast"):
        model.set_diff_mode(mode)
        assert model.get_diff_mode() == mode


def test_set_diff_mode_invalid():
    model = DirectorySyncModel()
    with pytest.raises(ValueError, match="Invalid diff mode"):
        model.set_diff_mode("turbo")
