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


def test_stop_crash_reproduction(tmp_path):
    """
    Regression test for crash when stopping synchronization.
    Verifies that stopping a heavy sync operation doesn't crash the process.
    """
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    # Create enough files to ensure the sync takes some time
    file_count = 1000
    files = create_dummy_files(dir1, file_count)

    entries = {}
    for path, meta in files.items():
        entries[path] = DiffEntry(relative_path=path, status=FileStatus.TO_COPY, source_meta=meta, target_meta=None)

    # Run a few iterations to catch race conditions
    for _i in range(3):
        diff = DiffResult(source_path=dir1, target_path=dir2, entries=entries)

        executor = DefaultSyncExecutor(num_workers=4)
        stop_event = threading.Event()

        # Thread to trigger stop after a short delay
        _stop_event = stop_event

        def stop_trigger(_evt=_stop_event):
            time.sleep(0.1)
            _evt.set()

        stopper = threading.Thread(target=stop_trigger)
        stopper.start()

        result = executor.execute(diff, stop_event=stop_event, progress_callback=lambda msg: None)

        stopper.join()

        # The test passes if we get here without a hard crash
        assert result is not None
        # We expect either a clean stop (empty errors or specific "Stopped" messages)
        # or a successful completion if it was too fast.
        # But crucially, no segfault/exception.
