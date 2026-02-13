# Copyright (C) 2026 nekoClangUage
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Utility functions and classes for the synchronization system.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class ThrottledProgressCallback:
    """
    Wrapper for progress callbacks that throttles update frequency.

    Prevents excessive UI updates by limiting how often the callback
    is actually invoked. This improves performance and reduces UI lag.
    """

    def __init__(
        self,
        callback: Callable[[str], None] | None,
        min_interval_ms: int = 100,
        *,
        force_final: bool = True,
    ):
        """
        Initialize the throttled callback.

        Args:
            callback: The actual callback to invoke
            min_interval_ms: Minimum milliseconds between invocations
            force_final: Whether to force the last message through on close
        """
        self._callback = callback
        self._min_interval = min_interval_ms / 1000.0
        self._force_final = force_final
        self._last_call_time = 0.0
        self._last_message: str | None = None
        self._lock = threading.Lock()

    def __call__(self, message: str) -> None:
        """Invoke the callback if enough time has passed."""
        if not self._callback:
            return

        current_time = time.time()

        with self._lock:
            self._last_message = message
            elapsed = current_time - self._last_call_time

            if elapsed >= self._min_interval:
                self._last_call_time = current_time
                self._callback(message)

    def flush(self) -> None:
        """Force the last message through if force_final is enabled."""
        if not self._callback or not self._force_final:
            return

        with self._lock:
            if self._last_message is not None:
                self._callback(self._last_message)
                self._last_message = None

    def __enter__(self) -> ThrottledProgressCallback:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.flush()


class StopChecker:
    """
    Utility for efficiently checking stop events.

    Reduces the overhead of checking stop events by only checking
    at specified intervals rather than on every operation.
    """

    def __init__(
        self,
        stop_event: threading.Event | None,
        check_interval: int = 100,
    ):
        """
        Initialize the stop checker.

        Args:
            stop_event: The threading.Event to check
            check_interval: Number of operations between actual checks
        """
        self._stop_event = stop_event
        self._check_interval = check_interval
        self._counter = 0
        self._is_stopped = False

    def should_stop(self) -> bool:
        """Check if the operation should stop."""
        if self._is_stopped:
            return True

        if not self._stop_event:
            return False

        self._counter += 1
        if self._counter >= self._check_interval:
            self._counter = 0
            self._is_stopped = self._stop_event.is_set()

        return self._is_stopped

    def force_check(self) -> bool:
        """Force an immediate check of the stop event."""
        if not self._stop_event:
            return False

        self._is_stopped = self._stop_event.is_set()
        return self._is_stopped


class BatchProcessor:
    """
    Utility for processing items in batches with progress reporting.

    Useful for operations that process many items and need to report
    progress without excessive overhead.
    """

    def __init__(
        self,
        total: int,
        batch_size: int = 100,
        progress_callback: Callable[[str], None] | None = None,
        message_format: str = "Processed {current}/{total}...",
    ):
        self._total = total
        self._batch_size = batch_size
        self._progress_callback = progress_callback
        self._message_format = message_format
        self._current = 0

    def increment(self, count: int = 1) -> None:
        """Increment the processed count and report if needed."""
        self._current += count

        if self._progress_callback and self._current % self._batch_size == 0:
            message = self._message_format.format(
                current=self._current,
                total=self._total,
            )
            self._progress_callback(message)

    def finish(self) -> None:
        """Report final progress."""
        if self._progress_callback:
            message = self._message_format.format(
                current=self._current,
                total=self._total,
            )
            self._progress_callback(message)

    @property
    def current(self) -> int:
        return self._current

    @property
    def total(self) -> int:
        return self._total
