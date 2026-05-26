"""Shared internals for taskbadger's optional system integrations
(Celery, Procrastinate). Not part of the public API.

Each integration creates its own module-level ``TaskCache`` instance and
defines a thin ``safe_get_task`` wrapper around the shared one defined here.
``BaseSystemIntegration`` provides the common ctor/include-exclude shape;
subclasses override ``track_task`` if they need to filter additional
task names (e.g. Procrastinate built-ins).
"""

from __future__ import annotations

import collections
import logging
import re

from . import sdk
from .internal.models import StatusEnum
from .systems import System

log = logging.getLogger("taskbadger")

TERMINAL_STATES = {
    StatusEnum.SUCCESS,
    StatusEnum.ERROR,
    StatusEnum.CANCELLED,
    StatusEnum.STALE,
}


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


def safe_get_task(cache: TaskCache, task_id: str):
    """Cache-aware ``get_task``: returns the cached entry if present, otherwise
    fetches via the SDK ``get_task`` and caches the result. Errors are logged and
    swallowed (returns ``None``). ``None`` results are not cached.
    """
    cached = cache.get(task_id)
    if cached is not None:
        return cached
    try:
        task = sdk.get_task(task_id)
    except Exception as e:
        log.warning("Error fetching task '%s': %s", task_id, e)
        return None
    cache.set(task_id, task)
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


class BaseSystemIntegration(System):
    """Common ctor + ``track_task`` body for system integrations.

    Subclasses set ``identifier`` and may override ``track_task`` to add
    additional filtering (e.g. skipping built-in tasks).
    """

    def __init__(self, auto_track_tasks=True, includes=None, excludes=None, record_task_args=False):
        self.auto_track_tasks = auto_track_tasks
        self.includes = includes
        self.excludes = excludes
        self.record_task_args = record_task_args

    def track_task(self, task_name: str) -> bool:
        if not self.auto_track_tasks:
            return False
        return match_task_name(task_name, self.includes, self.excludes)
