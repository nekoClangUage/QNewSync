import threading
import time
from pathlib import Path

from ui.workers import CancelWorkerThread, CompareWorkerThread, SyncWorkerThread


# Helper function
def create_test_files(directory: Path, count: int, content_prefix: str = "content"):
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        file_path = directory / f"file_{i}.txt"
        file_path.write_text(f"{content_prefix} {i}", encoding="utf-8")


def test_full_sync_flow_ui(qtbot, sync_model, tmp_path):
    """
    Test the full happy path: Compare -> Sync using Worker Threads.
    This simulates the actual UI interaction pattern.
    """
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    create_test_files(dir1, 10)
    dir2.mkdir()

    sync_model.set_directories(str(dir1), str(dir2))

    # 1. Compare
    # UI creates a CompareWorkerThread and starts it
    compare_worker = CompareWorkerThread(sync_model)

    # We use qtbot to wait for the signal
    with qtbot.waitSignal(compare_worker.finished, timeout=5000) as blocker:
        compare_worker.start()

    result = blocker.args[0]
    # result structure: (files_to_copy, files_to_replace, files_only_in_target, files_unchanged)
    # Since dir2 is empty, all 10 files should be in files_to_copy
    assert len(result[0]) == 10
    assert len(result[1]) == 0
    assert len(result[2]) == 0

    # 2. Sync
    # UI creates a SyncWorkerThread and starts it
    sync_worker = SyncWorkerThread(sync_model)

    with qtbot.waitSignal(sync_worker.finished, timeout=10000) as blocker:
        sync_worker.start()

    res = blocker.args[0]
    # SyncWorkerThread returns a dict from model.synchronize()
    # Keys are 'copied', 'replaced', 'skipped', 'unchanged', 'errors'
    assert res.get("copied") == 10
    assert len(list(dir2.glob("*.txt"))) == 10


def test_stop_and_rollback_flow_ui(qtbot, sync_model, tmp_path):
    """
    Test the flow: Sync -> Stop (User Interrupt) -> Cancel (Rollback).
    This ensures that partial syncs are handled and cleanup works.
    """
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    # Create enough files to ensure we can catch it mid-execution
    create_test_files(dir1, 500)
    dir2.mkdir()

    sync_model.set_directories(str(dir1), str(dir2))

    # Compare first (required for sync to know what to do usually,
    # though synchronise() re-runs scan/compare, the UI flow does compare first)
    sync_model.compare_directories()

    sync_worker = SyncWorkerThread(sync_model)

    # Logic to trigger stop mid-flight
    def trigger_stop():
        # Wait for a brief moment or until some files appear
        start_time = time.time()
        while time.time() - start_time < 5.0:
            if len(list(dir2.glob("*.txt"))) >= 10:
                break
            time.sleep(0.01)
        sync_model.stop()

    stopper = threading.Thread(target=trigger_stop)

    # Start sync and stop trigger
    with qtbot.waitSignal(sync_worker.finished, timeout=10000):
        sync_worker.start()
        stopper.start()
        stopper.join()

    # Verify incomplete state
    copied_files_count = len(list(dir2.glob("*.txt")))
    assert 0 < copied_files_count < 500, "Sync should have stopped partially"

    # Now trigger Cancel (Rollback)
    cancel_worker = CancelWorkerThread(sync_model)
    with qtbot.waitSignal(cancel_worker.finished, timeout=10000) as blocker:
        cancel_worker.start()

    errors = blocker.args[0]
    assert not errors, f"Rollback produced errors: {errors}"

    # Verify Cleanup
    remaining_files = len(list(dir2.glob("*.txt")))
    assert remaining_files == 0, f"Rollback failed to clean up. Remaining: {remaining_files}"


def test_backup_restore_ui_integration(qtbot, sync_model, tmp_path):
    """
    Test that files are backed up when replaced, and restored on rollback.
    Verifies the integrity of the backup/restore mechanism via UI workers.
    """
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    dir1.mkdir()
    dir2.mkdir()

    # File in both, but different content (triggers replace)
    # We use different lengths to guarantee TwoPhase diff strategy picks it up
    # even if mtimes are identical (which happens in fast tests).
    file_path1 = dir1 / "important.txt"
    file_path1.write_text("New Content Longer", encoding="utf-8")

    file_path2 = dir2 / "important.txt"
    file_path2.write_text("Old Content", encoding="utf-8")

    sync_model.set_directories(str(dir1), str(dir2))
    sync_model.compare_directories()

    # Sync (Replace)
    sync_worker = SyncWorkerThread(sync_model)
    with qtbot.waitSignal(sync_worker.finished, timeout=5000):
        sync_worker.start()

    # Verify replacement
    assert (dir2 / "important.txt").read_text(encoding="utf-8") == "New Content Longer"

    # Rollback (Cancel)
    cancel_worker = CancelWorkerThread(sync_model)
    with qtbot.waitSignal(cancel_worker.finished, timeout=5000):
        cancel_worker.start()

    # Verify restoration
    assert (dir2 / "important.txt").read_text(encoding="utf-8") == "Old Content"
