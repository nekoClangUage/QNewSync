"""
Tests for sync.utils module.
"""

import threading
import time

from sync.utils import (
    BatchProcessor,
    StopChecker,
    ThrottledProgressCallback,
)


class TestThrottledProgressCallback:
    """Tests for ThrottledProgressCallback."""

    def test_throttling(self):
        calls = []
        callback = ThrottledProgressCallback(
            lambda msg: calls.append(msg),
            min_interval_ms=100,
        )

        # Rapid calls should be throttled
        for i in range(10):
            callback(f"Message {i}")

        # Only first call should go through immediately
        assert len(calls) == 1
        assert calls[0] == "Message 0"

    def test_respects_interval(self):
        calls = []
        callback = ThrottledProgressCallback(
            lambda msg: calls.append(msg),
            min_interval_ms=50,
        )

        callback("First")
        time.sleep(0.1)  # Wait longer than interval
        callback("Second")

        assert len(calls) == 2

    def test_flush(self):
        calls = []
        callback = ThrottledProgressCallback(
            lambda msg: calls.append(msg),
            min_interval_ms=1000,
            force_final=True,
        )

        callback("First")
        callback("Last")  # This won't go through due to throttling

        callback.flush()

        assert "Last" in calls

    def test_context_manager(self):
        calls = []
        with ThrottledProgressCallback(
            lambda msg: calls.append(msg),
            min_interval_ms=1000,
            force_final=True,
        ) as callback:
            callback("First")
            callback("Last")

        # Flush should be called on exit
        assert "Last" in calls

    def test_none_callback(self):
        callback = ThrottledProgressCallback(None)
        callback("Test")  # Should not raise
        callback.flush()  # Should not raise


class TestStopChecker:
    """Tests for StopChecker."""

    def test_no_event(self):
        checker = StopChecker(None)
        assert checker.should_stop() is False
        assert checker.force_check() is False

    def test_event_not_set(self):
        event = threading.Event()
        checker = StopChecker(event, check_interval=1)
        assert checker.should_stop() is False

    def test_event_set(self):
        event = threading.Event()
        event.set()
        checker = StopChecker(event, check_interval=1)
        assert checker.should_stop() is True

    def test_interval_checking(self):
        event = threading.Event()
        checker = StopChecker(event, check_interval=5)

        # First 4 checks should not actually check the event
        for _ in range(4):
            checker.should_stop()

        # Set the event
        event.set()

        # 5th check should detect it
        assert checker.should_stop() is True

    def test_force_check(self):
        event = threading.Event()
        checker = StopChecker(event, check_interval=1000)

        # Normal check with high interval won't detect immediately
        checker.should_stop()

        event.set()

        # Force check should detect immediately
        assert checker.force_check() is True

    def test_stays_stopped(self):
        event = threading.Event()
        checker = StopChecker(event, check_interval=1)

        event.set()
        checker.should_stop()

        event.clear()

        # Should still report stopped
        assert checker.should_stop() is True


class TestBatchProcessor:
    """Tests for BatchProcessor."""

    def test_reports_at_intervals(self):
        messages = []
        processor = BatchProcessor(
            total=1000,
            batch_size=100,
            progress_callback=lambda msg: messages.append(msg),
        )

        for _ in range(250):
            processor.increment()

        assert len(messages) == 2  # At 100 and 200

    def test_finish_reports(self):
        messages = []
        processor = BatchProcessor(
            total=50,
            batch_size=100,
            progress_callback=lambda msg: messages.append(msg),
        )

        for _ in range(50):
            processor.increment()

        processor.finish()

        assert len(messages) == 1
        assert "50" in messages[0]

    def test_increment_count(self):
        processor = BatchProcessor(total=100, batch_size=10)

        processor.increment(5)
        assert processor.current == 5

        processor.increment(3)
        assert processor.current == 8

    def test_no_callback(self):
        processor = BatchProcessor(total=100, batch_size=10, progress_callback=None)

        for _ in range(100):
            processor.increment()

        processor.finish()  # Should not raise

    def test_custom_message_format(self):
        messages = []
        processor = BatchProcessor(
            total=100,
            batch_size=50,
            progress_callback=lambda msg: messages.append(msg),
            message_format="Done: {current} of {total}",
        )

        for _ in range(50):
            processor.increment()

        assert "Done: 50 of 100" in messages
