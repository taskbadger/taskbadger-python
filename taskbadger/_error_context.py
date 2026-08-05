"""Builds the `data` payload attached to a task when it errors, combining the
exception message with any registered `context_providers` (e.g. Sentry). Not
part of the public API.
"""

import logging
from contextvars import ContextVar

from taskbadger.mug import Badger

log = logging.getLogger("taskbadger")

_snapshots: ContextVar[dict] = ContextVar("taskbadger_context_snapshots", default=None)


def _providers():
    settings = Badger.current.settings
    return settings.context_providers if settings else []


def start_error_context():
    """Snapshot every configured context provider. Call this when a tracked task
    starts, before user code runs, so `capture_error_data` can later tell a fresh
    capture from a stale one left over from something unrelated.

    Returns a token that can be passed to `reset_error_context` to restore the
    previous snapshot (for nested tracking within the same thread).
    """
    snapshot = {}
    for provider in _providers():
        try:
            snapshot[provider.identifier] = provider.snapshot()
        except Exception:
            log.warning("Error snapshotting context provider '%s'", provider.identifier, exc_info=True)
    return _snapshots.set(snapshot)


def reset_error_context(token) -> None:
    _snapshots.reset(token)


def capture_error_data(exception: BaseException, message: str = None) -> dict:
    """Arguments:
    exception: The exception to report to context providers.
    message: Text to store as `data["exception"]`. Defaults to `str(exception)`;
        override when the caller has a more descriptive representation (e.g. Celery's
        `ExceptionInfo`, which wraps the original exception).
    """
    data = {"exception": message if message is not None else str(exception)}
    snapshot = _snapshots.get() or {}
    for provider in _providers():
        try:
            extra = provider.capture_error_context(exception, snapshot.get(provider.identifier))
        except Exception:
            log.warning("Error capturing context from provider '%s'", provider.identifier, exc_info=True)
            extra = None
        if extra:
            data[provider.identifier] = extra
    return data
