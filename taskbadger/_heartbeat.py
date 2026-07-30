"""Background heartbeat support for the system integrations (Celery,
Procrastinate). Not part of the public API.

A task that sets ``stale_timeout`` is marked ``stale`` by the API if it goes
too long without an update. Long-running queue tasks that don't report progress
would trip that timeout while perfectly healthy, so the integrations can ping
the task periodically for the duration of the run.

All in-flight tasks are pinged from a single daemon thread rather than one
thread per task. The thread is started lazily on first use and sleeps
indefinitely while nothing is registered.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
import time

from ._integrations import TERMINAL_STATES, is_valid_interval
from .mug import Badger, Settings
from .safe_sdk import update_task_safe

log = logging.getLogger("taskbadger")


@dataclasses.dataclass
class _Entry:
    interval: float
    settings: Settings
    due: float


class Heartbeat:
    """Periodically pings registered tasks to keep them from going stale."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}
        self._wake = threading.Event()
        self._thread = None

    def start(self, task_id: str, interval: float | None) -> None:
        """Begin pinging ``task_id`` every ``interval`` seconds.

        No-op if there is no interval or Task Badger isn't configured in the
        calling thread. Registering the same task again resets its schedule.
        """
        if not task_id or not is_valid_interval(interval):
            return

        settings = Badger.current.settings
        if settings is None:
            return

        with self._lock:
            self._entries[task_id] = _Entry(interval, settings, time.monotonic() + interval)
            self._ensure_thread()
        self._wake.set()

    def stop(self, task_id: str) -> None:
        """Stop pinging ``task_id``. No-op if it isn't registered."""
        with self._lock:
            self._entries.pop(task_id, None)

    def stop_all(self) -> None:
        with self._lock:
            self._entries.clear()

    def _ensure_thread(self) -> None:
        """Start the beat thread if it isn't running. Called with the lock held."""
        if self._thread is not None and self._thread.is_alive():
            return

        # `is_alive()` is also False for a thread inherited from a parent
        # process, so a forked worker (e.g. Celery's prefork pool) starts its
        # own thread the first time it runs a tracked task.
        self._thread = threading.Thread(target=self._run, name="taskbadger-heartbeat", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                timeout = self._beat()
            except Exception:
                # Never let the thread die: every registered task would then go
                # stale with nothing to restart the pings.
                log.exception("heartbeat beat failed")
                timeout = 1.0
            self._wake.wait(timeout)
            self._wake.clear()

    def _beat(self) -> float | None:
        """Ping every task that is due and return the seconds to sleep for.

        ``None`` means "sleep until a task is registered".
        """
        now = time.monotonic()
        with self._lock:
            due = [(task_id, entry) for task_id, entry in self._entries.items() if entry.due <= now]
            for _, entry in due:
                entry.due = now + entry.interval

        for task_id, entry in due:
            self._ping(task_id, entry)

        with self._lock:
            if not self._entries:
                return None
            next_due = min(entry.due for entry in self._entries.values())
        return max(next_due - time.monotonic(), 0)

    def _ping(self, task_id: str, entry: _Entry) -> None:
        # The beat thread has its own context, so bind the settings captured
        # when the task registered rather than relying on inheritance.
        if Badger.current.settings is not entry.settings:
            Badger.current.bind(entry.settings)

        log.debug("heartbeat ping '%s'", task_id)
        task = update_task_safe(task_id)
        if task is not None and task.status in TERMINAL_STATES:
            # The task finished (or was cancelled) elsewhere.
            self.stop(task_id)


heartbeat = Heartbeat()
