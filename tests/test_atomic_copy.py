"""Content-level checks for staged copies, process termination and operation-owned cleanup."""

from __future__ import annotations

import multiprocessing
import os
import shutil
import threading
import time
from collections.abc import Callable
from multiprocessing.managers import EventProxy
from pathlib import Path

import pytest

from sync.interfaces import DiffEntry, DiffResult, FileMeta, FileStatus, StopEvent, SyncResult
from sync.strategies import (
    CopyWorkerResult,
    DefaultSyncExecutor,
    _copy_worker,
    _prepare_temporary_path,
    _remove_temporary_files,
)


def _make_diff(source: Path, target: Path, *, replacements: bool) -> DiffResult:
    entries: dict[Path, DiffEntry] = {}
    for path in source.glob("*.txt"):
        relative_path: Path = path.relative_to(source)
        stat: os.stat_result = path.stat()
        meta: FileMeta = FileMeta(relative_path, path, stat.st_size, stat.st_mtime)
        status: FileStatus = FileStatus.TO_REPLACE if replacements else FileStatus.TO_COPY
        entries[relative_path] = DiffEntry(relative_path, status, source_meta=meta)
    return DiffResult(source, target, entries)


@pytest.mark.parametrize("is_replace", [False, True])
def test_success_installs_complete_file_and_preserves_backup(tmp_path: Path, is_replace: bool) -> None:
    source: Path = tmp_path / "source.txt"
    target: Path = tmp_path / "target" / "file.txt"
    source.write_bytes(b"new contents")
    os.utime(source, (1234567890, 1234567890))
    target.parent.mkdir()
    if is_replace:
        target.write_bytes(b"old contents")
    backup: Path = tmp_path / "backup"
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(target, directories)
    backup_temporary: Path | None = _prepare_temporary_path(backup / "file.txt", directories) if is_replace else None

    result: CopyWorkerResult = _copy_worker(
        source_path=source,
        target_path=target,
        rel_path=Path("file.txt"),
        is_replace=is_replace,
        backup_dir=backup if is_replace else None,
        mp_stop=None,
        temporary_path=temporary,
        backup_temporary_path=backup_temporary,
    )

    assert result == (Path("file.txt"), True, is_replace, None)
    assert target.read_bytes() == source.read_bytes() == b"new contents"
    assert target.stat().st_mtime == source.stat().st_mtime
    if is_replace:
        assert (backup / "file.txt").read_bytes() == b"old contents"
    assert not temporary.exists()
    assert _remove_temporary_files(directories.values()) == []


@pytest.mark.parametrize("is_replace", [False, True])
def test_partial_copy_error_does_not_change_final_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, is_replace: bool
) -> None:
    source: Path = tmp_path / "source.txt"
    target: Path = tmp_path / "target.txt"
    source.write_bytes(b"complete new contents")
    if is_replace:
        target.write_bytes(b"complete old contents")
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(target, directories)
    backup: Path = tmp_path / "backup"
    backup_temporary: Path | None = _prepare_temporary_path(backup / "target.txt", directories) if is_replace else None

    def fail_mid_copy(source_path: Path, destination_path: Path) -> None:
        destination_path.write_bytes(b"partial")
        raise OSError("simulated mid-copy failure")

    monkeypatch.setattr("sync.strategies.shutil.copy2", fail_mid_copy)
    result: CopyWorkerResult = _copy_worker(
        source_path=source,
        target_path=target,
        rel_path=Path("target.txt"),
        is_replace=is_replace,
        backup_dir=backup if is_replace else None,
        mp_stop=None,
        temporary_path=temporary,
        backup_temporary_path=backup_temporary,
    )

    assert result[1] is False
    assert result[3] == "simulated mid-copy failure"
    assert source.read_bytes() == b"complete new contents"
    if is_replace:
        assert target.read_bytes() == b"complete old contents"
        assert not (backup / "target.txt").exists()
    else:
        assert not target.exists()
    assert not temporary.exists()
    assert _remove_temporary_files(directories.values()) == []


@pytest.mark.parametrize("stop_after", [0, 1, 2])
def test_stop_before_install_keeps_old_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop_after: int) -> None:
    source: Path = tmp_path / "source.txt"
    target: Path = tmp_path / "target.txt"
    source.write_bytes(b"new contents")
    target.write_bytes(b"old contents")
    backup: Path = tmp_path / "backup"
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(target, directories)
    backup_temporary: Path = _prepare_temporary_path(backup / "target.txt", directories)
    stop: threading.Event = threading.Event()
    if stop_after == 0:
        stop.set()
    original_copy: Callable[[Path, Path], Path] = shutil.copy2
    calls: int = 0

    def copy_and_stop(source_path: Path, destination_path: Path) -> None:
        nonlocal calls
        original_copy(source_path, destination_path)
        calls += 1
        if calls == stop_after:
            stop.set()

    monkeypatch.setattr("sync.strategies.shutil.copy2", copy_and_stop)
    result: CopyWorkerResult = _copy_worker(
        source_path=source,
        target_path=target,
        rel_path=Path("target.txt"),
        is_replace=True,
        backup_dir=backup,
        mp_stop=stop,
        temporary_path=temporary,
        backup_temporary_path=backup_temporary,
    )

    assert result == (Path("target.txt"), False, True, "Stopped")
    assert source.read_bytes() == b"new contents"
    assert target.read_bytes() == b"old contents"
    assert not (backup / "target.txt").exists()
    assert not temporary.exists()
    assert not backup_temporary.exists()
    assert _remove_temporary_files(directories.values()) == []


def test_failed_backup_does_not_publish_partial_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source: Path = tmp_path / "source.txt"
    target: Path = tmp_path / "target.txt"
    source.write_bytes(b"new contents")
    target.write_bytes(b"old contents")
    backup: Path = tmp_path / "backup"
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(target, directories)
    backup_temporary: Path = _prepare_temporary_path(backup / "target.txt", directories)
    (backup / "target.txt").write_bytes(b"previous complete backup")
    original_copy: Callable[[Path, Path], Path] = shutil.copy2

    def fail_backup(source_path: Path, destination_path: Path) -> None:
        if source_path == target:
            destination_path.write_bytes(b"partial backup")
            raise OSError("simulated backup failure")
        original_copy(source_path, destination_path)

    monkeypatch.setattr("sync.strategies.shutil.copy2", fail_backup)
    result: CopyWorkerResult = _copy_worker(
        source_path=source,
        target_path=target,
        rel_path=Path("target.txt"),
        is_replace=True,
        backup_dir=backup,
        mp_stop=None,
        temporary_path=temporary,
        backup_temporary_path=backup_temporary,
    )

    assert result[1] is False
    assert result[3] == "simulated backup failure"
    assert source.read_bytes() == b"new contents"
    assert target.read_bytes() == b"old contents"
    assert (backup / "target.txt").read_bytes() == b"previous complete backup"
    assert not temporary.exists()
    assert not backup_temporary.exists()
    assert _remove_temporary_files(directories.values()) == []


def test_failed_install_keeps_old_file_and_complete_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source: Path = tmp_path / "source.txt"
    target: Path = tmp_path / "target.txt"
    source.write_bytes(b"new contents")
    target.write_bytes(b"old contents")
    backup: Path = tmp_path / "backup"
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(target, directories)
    backup_temporary: Path = _prepare_temporary_path(backup / "target.txt", directories)
    original_replace: Callable[[Path, Path], None] = os.replace

    def fail_install(source_path: Path, destination_path: Path) -> None:
        if destination_path == target:
            raise PermissionError("simulated install failure")
        original_replace(source_path, destination_path)

    monkeypatch.setattr("sync.strategies.os.replace", fail_install)
    result: CopyWorkerResult = _copy_worker(
        source_path=source,
        target_path=target,
        rel_path=Path("target.txt"),
        is_replace=True,
        backup_dir=backup,
        mp_stop=None,
        temporary_path=temporary,
        backup_temporary_path=backup_temporary,
    )

    assert result[1] is False
    assert result[3] == "simulated install failure"
    assert source.read_bytes() == b"new contents"
    assert target.read_bytes() == (backup / "target.txt").read_bytes() == b"old contents"
    assert not temporary.exists()
    assert _remove_temporary_files(directories.values()) == []


def test_cleanup_failure_is_reported_and_leaves_foreign_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directories: dict[Path, Path] = {}
    temporary: Path = _prepare_temporary_path(tmp_path / "target.txt", directories)
    temporary.write_bytes(b"partial")
    foreign_file: Path = tmp_path / "user.tmp"
    foreign_file.write_bytes(b"user data")

    def fail_remove(path: Path) -> None:
        raise PermissionError("simulated cleanup failure")

    monkeypatch.setattr("sync.strategies.shutil.rmtree", fail_remove)
    errors: list[str] = _remove_temporary_files(directories.values())
    assert len(errors) == 1
    assert str(temporary.parent) in errors[0]
    assert "simulated cleanup failure" in errors[0]
    assert foreign_file.read_bytes() == b"user data"


@pytest.mark.parametrize("start_method", ["default", "spawn"])
def test_parallel_named_tasks_copy_replace_and_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, start_method: str
) -> None:
    if start_method == "spawn":
        monkeypatch.setattr("sync.strategies.Pool", multiprocessing.get_context("spawn").Pool)
    source: Path
    target: Path
    backup: Path
    source, target, backup = tmp_path / "source", tmp_path / "target", tmp_path / "backup"
    source.mkdir()
    target.mkdir()
    old_files: dict[str, bytes] = {}
    for index in range(12):
        name: str = f"file-{index}.txt"
        old_files[name] = f"old-{index}".encode()
        (source / name).write_bytes(f"new-{index}".encode())
        (target / name).write_bytes(old_files[name])
    foreign: Path = target / "user.tmp"
    foreign.write_bytes(b"keep")
    executor: DefaultSyncExecutor = DefaultSyncExecutor(num_workers=3)
    result: SyncResult = executor.execute(_make_diff(source, target, replacements=True), backup_dir=backup)

    assert result.errors == []
    assert result.replaced_count == 12
    for name, old in old_files.items():
        assert (target / name).read_bytes() == (source / name).read_bytes()
        assert (backup / name).read_bytes() == old
    assert not list(target.rglob(".qnewsync-*"))
    assert not list(backup.rglob(".qnewsync-*"))
    assert foreign.read_bytes() == b"keep"
    assert executor.rollback() == []
    for name, old in old_files.items():
        assert (target / name).read_bytes() == old


def _controlled_copy_worker(
    *,
    source_path: Path,
    target_path: Path,
    rel_path: Path,
    is_replace: bool,
    backup_dir: Path | None,
    mp_stop: EventProxy | StopEvent | None,
    temporary_path: Path,
    backup_temporary_path: Path | None,
) -> CopyWorkerResult:
    """Keep one real pool process inside a partial write until the coordinator terminates it."""
    if rel_path.name.startswith("blocked"):
        if rel_path.name == "blocked-backup.txt":
            shutil.copy2(source_path, temporary_path)
            assert backup_temporary_path is not None
            backup_temporary_path.write_bytes(b"partial backup")
        else:
            temporary_path.write_bytes(b"partial")
        (source_path.parent / "copy-started").touch()
        time.sleep(30)
        raise TimeoutError("Blocked worker was not terminated")
    deadline: float = time.monotonic() + 5
    while not (source_path.parent / "stop-requested").exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("Stop observer did not run")
        time.sleep(0.01)
    return _copy_worker(
        source_path=source_path,
        target_path=target_path,
        rel_path=rel_path,
        is_replace=is_replace,
        backup_dir=backup_dir,
        mp_stop=mp_stop,
        temporary_path=temporary_path,
        backup_temporary_path=backup_temporary_path,
    )


@pytest.mark.parametrize("blocked_name", ["blocked.txt", "blocked-backup.txt"])
def test_terminated_process_leaves_old_file_and_coordinator_removes_its_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocked_name: str
) -> None:
    source: Path
    target: Path
    backup: Path
    source, target, backup = tmp_path / "source", tmp_path / "target", tmp_path / "backup"
    source.mkdir()
    target.mkdir()
    for name in [blocked_name, "fast.txt"]:
        (source / name).write_bytes(b"complete new contents")
        (target / name).write_bytes(b"complete old contents")
    foreign: Path = target / ".qnewsync-user"
    foreign.mkdir()
    (foreign / "user.tmp").write_bytes(b"keep")
    monkeypatch.setattr("sync.strategies._copy_worker", _controlled_copy_worker)
    stop: threading.Event = threading.Event()

    def request_stop() -> None:
        deadline: float = time.monotonic() + 5
        while not (source / "copy-started").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        stop.set()
        (source / "stop-requested").touch()

    observer: threading.Thread = threading.Thread(target=request_stop)
    observer.start()
    try:
        result: SyncResult = DefaultSyncExecutor(num_workers=2).execute(
            _make_diff(source, target, replacements=True), backup_dir=backup, stop_event=stop
        )
    finally:
        observer.join(timeout=6)

    assert not observer.is_alive()
    assert (source / "copy-started").exists()
    assert result.errors == []
    assert (target / blocked_name).read_bytes() == b"complete old contents"
    assert (source / blocked_name).read_bytes() == b"complete new contents"
    assert not (backup / blocked_name).exists()
    assert (target / "fast.txt").read_bytes() in (b"complete old contents", b"complete new contents")
    assert list(target.rglob(".qnewsync-*")) == [foreign]
    assert not list(backup.rglob(".qnewsync-*"))
    assert (foreign / "user.tmp").read_bytes() == b"keep"
