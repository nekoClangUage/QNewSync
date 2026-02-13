
import pytest

from sync.directory_sync_model import DirectorySyncModel


@pytest.fixture
def temp_dirs(tmp_path):
    """Create source and target directories for testing."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    return source, target

def test_empty_directories_ignored_by_default(temp_dirs):
    """Verify that empty directories are NOT copied by default."""
    source, target = temp_dirs

    # Create an empty directory in source
    (source / "empty_dir").mkdir()

    # Create a file in a nested directory to ensure the parent IS copied
    (source / "nested").mkdir()
    (source / "nested" / "file.txt").write_text("content")

    model = DirectorySyncModel()
    model.set_directories(str(source), str(target))

    # Run sync
    model.synchronize()

    # Verify results
    assert (target / "nested").exists()
    assert (target / "nested" / "file.txt").exists()

    # Default behavior: empty_dir should NOT exist
    assert not (target / "empty_dir").exists()

def test_empty_directories_copied_when_enabled(temp_dirs):
    """Verify that empty directories ARE copied when the setting is enabled."""
    source, target = temp_dirs

    # Create structure:
    # source/
    #   empty_dir/          (should be copied)
    #   nested_empty/       (should be copied)
    #     deep_empty/       (should be copied)
    #   mixed/              (should be copied because it has files)
    #     file.txt

    (source / "empty_dir").mkdir()
    (source / "nested_empty").mkdir()
    (source / "nested_empty" / "deep_empty").mkdir()
    (source / "mixed").mkdir()
    (source / "mixed" / "file.txt").write_text("content")

    model = DirectorySyncModel()
    model.set_directories(str(source), str(target))

    # Enable copy_empty_dirs using set_filters
    model.set_filters(ignore_hidden=True, copy_empty_dirs=True)

    model.synchronize()

    assert (target / "empty_dir").exists()
    assert (target / "empty_dir").is_dir()
    assert (target / "nested_empty").exists()
    assert (target / "nested_empty" / "deep_empty").exists()
    assert (target / "mixed").exists()
    assert (target / "mixed" / "file.txt").exists()
