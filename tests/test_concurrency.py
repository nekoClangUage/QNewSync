import time

import pytest

from sync.directory_sync_model import DirectorySyncModel
from ui.workers import CancelWorkerThread, SyncWorkerThread


@pytest.fixture
def heavy_model(tmp_path):
    """Model with enough work to sustain threads for a moment."""
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    dir1.mkdir()
    dir2.mkdir()

    # Create 500 small files to give the sync process something to chew on
    for i in range(500):
        (dir1 / f"f_{i}.dat").write_text("x" * 100, encoding="utf-8")

    model = DirectorySyncModel()
    model.set_directories(str(dir1), str(dir2))
    return model


def test_rapid_start_stop_race_condition(qtbot, heavy_model):
    """
    Stress test: Rapidly start and stop the sync thread.
    This attempts to trigger race conditions where stop() might be ignored
    or cause a crash if called too early/late.
    """
    heavy_model.compare_directories()

    # We loop a few times to increase probability of hitting a race
    for i in range(5):
        worker = SyncWorkerThread(heavy_model)

        worker.start()

        # We vary the sleep time slightly to hit different execution windows
        time.sleep(0.01 * (i % 3))

        # Request stop
        heavy_model.stop()

        # Wait for worker to finish (it should finish either fully done or stopped)
        with qtbot.waitSignal(worker.finished, timeout=5000):
            pass

        # The finished signal is emitted inside run(), so the thread is technically
        # still running for a brief moment. We wait for it to fully exit.
        worker.wait()

        assert worker.isFinished()

        # Clean up for next iteration
        heavy_model.reset_stop()
        # We don't strictly assert that it stopped because of the race condition mentioned
        # (reset_stop inside synchronize), but we assert it doesn't crash.


def test_concurrent_cancel_requests(qtbot, heavy_model):
    """
    Test invoking rollback while another operation might be concluding or multiple cancels.
    Ensures that rollback is idempotent and thread-safe.
    """
    heavy_model.compare_directories()

    # 1. Start Sync
    worker = SyncWorkerThread(heavy_model)
    worker.start()

    # Let it run a tiny bit
    time.sleep(0.1)

    # 2. Stop it
    heavy_model.stop()
    worker.wait(2000)

    # 3. Start Rollback (Cancel)
    cancel_worker = CancelWorkerThread(heavy_model)

    with qtbot.waitSignal(cancel_worker.finished, timeout=5000) as blocker:
        cancel_worker.start()

        # 4. Attempt to trigger another rollback or call rollback_changes directly
        # while the thread is running. This simulates a user mashing the button
        # or logic overlap.
        # Note: In the UI, the button is usually disabled, but the underlying model
        # should be robust.
        errors = heavy_model.rollback_changes()

    # The threaded rollback should have finished
    threaded_errors = blocker.args[0]

    assert isinstance(threaded_errors, list)
    assert isinstance(errors, list)

    # Verify we didn't crash and model is in stable state
    assert not heavy_model.stop_event.is_set()  # reset_stop is called in rollback


def test_thread_cleanup_safety(qtbot, heavy_model):
    """
    Verify that threads clean up resources properly even if terminated early.
    """
    heavy_model.compare_directories()

    worker = SyncWorkerThread(heavy_model)

    with qtbot.waitSignal(worker.finished, timeout=5000):
        worker.start()
        heavy_model.stop()

    # Check if we can immediately start another one without issues
    worker2 = SyncWorkerThread(heavy_model)
    with qtbot.waitSignal(worker2.finished, timeout=5000):
        worker2.start()
        heavy_model.stop()
