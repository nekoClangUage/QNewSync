import threading
from pathlib import Path

from sync.interfaces import DiffEntry, DiffResult, FileMeta, FileStatus
from sync.strategies import DefaultSyncExecutor


def _create_meta(base_dir: Path, rel_path: Path) -> FileMeta:
    file_path = base_dir / rel_path
    stat = file_path.stat()
    return FileMeta(
        relative_path=rel_path,
        absolute_path=file_path,
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


def _build_diff(
    *,
    source_dir: Path,
    target_dir: Path,
    copy_paths: list[Path],
    replace_paths: list[Path],
) -> DiffResult:
    entries: dict[Path, DiffEntry] = {}

    for rel_path in copy_paths:
        source_meta = _create_meta(source_dir, rel_path)
        entries[rel_path] = DiffEntry(rel_path, FileStatus.TO_COPY, source_meta, None)

    for rel_path in replace_paths:
        source_meta = _create_meta(source_dir, rel_path)
        target_meta = _create_meta(target_dir, rel_path)
        entries[rel_path] = DiffEntry(rel_path, FileStatus.TO_REPLACE, source_meta, target_meta)

    return DiffResult(source_path=source_dir, target_path=target_dir, entries=entries)


def test_copy_files_parallel_copies_files(temp_dir):
    dir1 = temp_dir["dir1"]
    dir2 = temp_dir["dir2"]
    write_file = temp_dir["write_file"]

    files_to_copy = []
    expected_contents = {}
    for idx in range(6):
        rel_path = Path("nested") / f"file_{idx}.txt" if idx % 2 else Path(f"file_{idx}.txt")
        content = f"content-{idx}"
        write_file(dir1, rel_path, content)
        files_to_copy.append(rel_path)
        expected_contents[rel_path] = content

    diff = _build_diff(
        source_dir=dir1,
        target_dir=dir2,
        copy_paths=files_to_copy,
        replace_paths=[],
    )
    executor = DefaultSyncExecutor(num_workers=2)
    result = executor.execute(diff, stop_event=threading.Event())

    assert result.copied_count == len(files_to_copy)
    assert result.replaced_count == 0
    assert result.errors == []
    assert result.copied_files == set(files_to_copy)
    assert result.replaced_files == set()

    for rel_path, content in expected_contents.items():
        assert (dir2 / rel_path).read_text(encoding="utf-8") == content


def test_copy_files_parallel_replaces_and_backs_up(temp_dir, backup_dir):
    dir1 = temp_dir["dir1"]
    dir2 = temp_dir["dir2"]
    write_file = temp_dir["write_file"]

    rel_path = Path("nested") / "replace.txt"
    write_file(dir2, rel_path, "old")
    write_file(dir1, rel_path, "new")

    diff = _build_diff(
        source_dir=dir1,
        target_dir=dir2,
        copy_paths=[],
        replace_paths=[rel_path],
    )
    executor = DefaultSyncExecutor(num_workers=2)
    result = executor.execute(
        diff,
        stop_event=threading.Event(),
        backup_dir=backup_dir,
    )

    assert result.copied_count == 0
    assert result.replaced_count == 1
    assert result.errors == []
    assert result.copied_files == set()
    assert result.replaced_files == {rel_path}

    backup_path = backup_dir / rel_path
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "old"
    assert (dir2 / rel_path).read_text(encoding="utf-8") == "new"
