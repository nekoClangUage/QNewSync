import threading
import time
from pathlib import Path

from sync.interfaces import DiffEntry, DiffResult, FileMeta, FileStatus
from sync.strategies import DefaultSyncExecutor


def create_dummy_files(directory, count):
    files = {}
    for i in range(count):
        fname = f"file_{i}.txt"
        fpath = directory / fname
        fpath.write_text(f"content {i}")
        files[Path(fname)] = FileMeta(
            relative_path=Path(fname), absolute_path=fpath, size=len(f"content {i}"), mtime=fpath.stat().st_mtime
        )
    return files


def test_cancel_cleanup_after_stop(tmp_path):
    """
    Verifies that calling rollback after a stopped sync removes ALL copied files,
    even those that weren't acknowledged before the stop occurred.
    """
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Create files to copy
    file_count = 1000
    files = create_dummy_files(dir1, file_count)

    entries = {}
    for path, meta in files.items():
        entries[path] = DiffEntry(relative_path=path, status=FileStatus.TO_COPY, source_meta=meta, target_meta=None)

    diff = DiffResult(source_path=dir1, target_path=dir2, entries=entries)

    executor = DefaultSyncExecutor(num_workers=4)
    stop_event = threading.Event()

    # Trigger stop after a delay that ensures some copies happen
    def stop_trigger():
        # Wait until some files appear in dir2
        start = time.time()
        while time.time() - start < 5.0:
            if len(list(dir2.glob("*.txt"))) > 10:
                break
            time.sleep(0.01)
        stop_event.set()

    stopper = threading.Thread(target=stop_trigger)
    stopper.start()

    # Execute Sync
    executor.execute(diff, stop_event=stop_event, progress_callback=lambda msg: None)

    stopper.join()

    # At this point, some files should have been copied to dir2
    copied_count_actual = len(list(dir2.glob("*.txt")))
    print(f"Files in dir2 after stop: {copied_count_actual}")

    # Ensure at least some files were copied (otherwise test is invalid)
    assert copied_count_actual > 0, "No files were copied before stop, test invalid"

    # Verify that we have some untracked files (this confirms the bug exists)
    # executor._copied_files contains what the executor THINKS it copied
    print(f"Tracked files: {len(executor._copied_files)}")

    # NOW, perform rollback
    executor.rollback()

    # Verify Dir2 is empty (all copied files removed)
    remaining_files = list(dir2.glob("*.txt"))
    assert len(remaining_files) == 0, f"Rollback failed to remove {len(remaining_files)} files: {remaining_files}"
