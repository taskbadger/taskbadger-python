"""Shared internals for taskbadger's optional system integrations
(Celery, Procrastinate). Not part of the public API.

A single module-level ``TaskCache`` (``task_cache``) is shared across all
integrations; task ids are UUIDs so cross-integration key collisions are not
a concern. ``BaseSystemIntegration`` provides the common ctor/include-exclude
shape; subclasses override ``track_task`` if they need to filter additional
task names (e.g. Procrastinate built-ins).
"""

from __future__ import annotations

import collections
import logging
import re

from . import sdk
from .exceptions import ConfigurationError
from .internal.models import StatusEnum
from .systems import System

log = logging.getLogger("taskbadger")

TERMINAL_STATES = {
    StatusEnum.SUCCESS,
    StatusEnum.ERROR,
    StatusEnum.CANCELLED,
    StatusEnum.STALE,
}

# When a heartbeat is configured but no `stale_timeout` is given, the timeout
# is derived from the interval using this factor (as the CLI's `run` does).
STALE_TIMEOUT_FACTOR = 2


class TaskCache:
    """Bounded LRU-ish cache for TaskBadger Task objects.

    Keys are arbitrary hashable values chosen by the caller (typically the
    task id). Auto-prunes on ``set`` when ``maxsize`` is exceeded.
    """

    def __init__(self, maxsize: int = 128):
        self.cache: collections.OrderedDict = collections.OrderedDict()
        self.maxsize = maxsize

    def set(self, key, value) -> None:
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def get(self, key):
        return self.cache.get(key)

    def unset(self, key) -> None:
        self.cache.pop(key, None)


task_cache = TaskCache()


def safe_get_task(task_id: str):
    """Cache-aware ``get_task``: returns the cached entry if present, otherwise
    fetches from the API and caches the result. Errors are logged and swallowed
    (returns ``None``). ``None`` results are not cached.
    """
    cached = task_cache.get(task_id)
    if cached is not None:
        return cached
    try:
        task = sdk.get_task(task_id)
    except Exception as e:
        log.warning("Error fetching task '%s': %s", task_id, e)
        return None
    task_cache.set(task_id, task)
    return task


def match_task_name(task_name: str, includes, excludes) -> bool:
    """Return True if ``task_name`` should be tracked under the given rules.

    Excludes win over includes. Both lists contain regex strings matched with
    ``re.fullmatch``. ``None`` means "no rule".
    """
    if excludes:
        for exclude in excludes:
            if re.fullmatch(exclude, task_name):
                return False

    if includes:
        for include in includes:
            if re.fullmatch(include, task_name):
                return True
        return False

    return True


def is_valid_interval(interval) -> bool:
    """Return True if ``interval`` is usable as a heartbeat interval."""
    return isinstance(interval, int | float) and interval > 0


def validate_interval(interval) -> None:
    """Raise if ``interval`` is set but isn't usable as a heartbeat interval."""
    if interval is not None and not is_valid_interval(interval):
        raise ConfigurationError(f"heartbeat_interval must be a positive number of seconds: {interval!r}")


def resolve_heartbeat_options(heartbeat_interval, stale_timeout, system):
    """Resolve the heartbeat interval and stale timeout for a single task.

    Values set on the task win over those set on the system integration. If a
    heartbeat is configured without a stale timeout, one is derived from the
    interval.

    Returns:
        A tuple of ``(heartbeat_interval, stale_timeout)``, either of which may
        be ``None``.
    """
    if system is not None:
        if heartbeat_interval is None:
            heartbeat_interval = system.heartbeat_interval
        if stale_timeout is None:
            stale_timeout = system.stale_timeout

    if heartbeat_interval is not None and not is_valid_interval(heartbeat_interval):
        # Per-task values don't go through `validate_interval`, and a bad one
        # shouldn't stop the task from being tracked.
        log.warning("Ignoring invalid heartbeat_interval: %r", heartbeat_interval)
        heartbeat_interval = None

    if stale_timeout is None and heartbeat_interval:
        stale_timeout = int(heartbeat_interval * STALE_TIMEOUT_FACTOR)

    return heartbeat_interval, stale_timeout


class BaseSystemIntegration(System):
    """Common ctor + ``track_task`` body for system integrations.

    Subclasses set ``identifier`` and may override ``track_task`` to add
    additional filtering (e.g. skipping built-in tasks).
    """

    def __init__(
        self,
        auto_track_tasks=True,
        includes=None,
        excludes=None,
        record_task_args=False,
        heartbeat_interval=None,
        stale_timeout=None,
    ):
        validate_interval(heartbeat_interval)
        self.auto_track_tasks = auto_track_tasks
        self.includes = includes
        self.excludes = excludes
        self.record_task_args = record_task_args
        self.heartbeat_interval = heartbeat_interval
        self.stale_timeout = stale_timeout

    def track_task(self, task_name: str) -> bool:
        if not self.auto_track_tasks:
            return False
        return match_task_name(task_name, self.includes, self.excludes)
