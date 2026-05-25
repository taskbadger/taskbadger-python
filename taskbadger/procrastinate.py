"""TaskBadger integration for the Procrastinate task queue.

This module is opt-in. Users install Procrastinate themselves (or via the
``taskbadger[procrastinate]`` extra) and import from here.

Public API:
    - ``track``: decorator to opt a single task into TaskBadger tracking.
    - ``current_task()``: accessor for the TaskBadger task associated with the
      currently-running Procrastinate job (returns ``None`` if not tracked).
"""

from __future__ import annotations

import collections
import functools
import inspect
import logging
from contextvars import ContextVar

from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy, get_task

log = logging.getLogger("taskbadger")

# Reserved key used to smuggle the TaskBadger task id through Procrastinate's
# task_kwargs from the deferring process to the worker. Stripped before the
# user function is called.
TB_TASK_ID_KWARG = "__taskbadger_task_id__"

TERMINAL_STATES = {
    StatusEnum.SUCCESS,
    StatusEnum.ERROR,
    StatusEnum.CANCELLED,
    StatusEnum.STALE,
}

# Sentinel attribute names set on a Procrastinate Task object once it has been
# instrumented. Used to make instrumentation idempotent.
_INSTRUMENTED_ATTR = "_taskbadger_instrumented"
_MANUAL_ATTR = "_taskbadger_manual"
_OPTS_ATTR = "_taskbadger_opts"

_current_tb_task_id: ContextVar[str | None] = ContextVar("_current_tb_task_id", default=None)


def _instrument_task(task, system=None, manual=False, opts=None):
    """Wrap a Procrastinate Task's ``func`` so the worker side updates TaskBadger.

    Idempotent: a second call on the same task is a no-op (but ``manual`` and
    ``opts`` will be merged onto the existing attributes if provided).
    """
    if opts is not None:
        existing_opts = getattr(task, _OPTS_ATTR, {}) or {}
        merged = {**existing_opts, **opts}
        setattr(task, _OPTS_ATTR, merged)
    elif not hasattr(task, _OPTS_ATTR):
        setattr(task, _OPTS_ATTR, {})

    if manual:
        setattr(task, _MANUAL_ATTR, True)

    if getattr(task, _INSTRUMENTED_ATTR, False):
        return

    original_func = task.func
    is_async = inspect.iscoroutinefunction(original_func)

    if is_async:

        @functools.wraps(original_func)
        async def wrapped(*args, **kwargs):
            tb_id = kwargs.pop(TB_TASK_ID_KWARG, None)
            if tb_id is None:
                return await original_func(*args, **kwargs)
            token = _current_tb_task_id.set(tb_id)
            try:
                _update_status(tb_id, StatusEnum.PROCESSING)
                try:
                    result = await original_func(*args, **kwargs)
                except Exception as exc:
                    _update_status(tb_id, StatusEnum.ERROR, exception=exc)
                    raise
                _update_status(tb_id, StatusEnum.SUCCESS)
                return result
            finally:
                _current_tb_task_id.reset(token)
    else:

        @functools.wraps(original_func)
        def wrapped(*args, **kwargs):
            tb_id = kwargs.pop(TB_TASK_ID_KWARG, None)
            if tb_id is None:
                return original_func(*args, **kwargs)
            token = _current_tb_task_id.set(tb_id)
            try:
                _update_status(tb_id, StatusEnum.PROCESSING)
                try:
                    result = original_func(*args, **kwargs)
                except Exception as exc:
                    _update_status(tb_id, StatusEnum.ERROR, exception=exc)
                    raise
                _update_status(tb_id, StatusEnum.SUCCESS)
                return result
            finally:
                _current_tb_task_id.reset(token)

    _wrap_defer(task)
    task.func = wrapped
    setattr(task, _INSTRUMENTED_ATTR, True)
    setattr(task, "_taskbadger_system", system)


def _update_status(tb_id, status, exception=None):
    """Update the TaskBadger task to ``status``. Skips if already terminal."""
    if not Badger.is_configured():
        return

    if exception is not None or status in TERMINAL_STATES:
        # Bypass the cache for the terminal-state check: the user may have
        # updated the task to a terminal state via the regular SDK during
        # the body, which wouldn't be reflected in our local cache.
        _task_cache.unset(tb_id)
        current = _safe_get_task(tb_id)
        if current is not None and current.status in TERMINAL_STATES:
            return
        data = None
        if exception is not None and current is not None:
            base = dict(current.data) if current.data else None
            data = DefaultMergeStrategy().merge(base, {"exception": str(exception)})
        if data is not None:
            updated = update_task_safe(tb_id, status=status, data=data)
        else:
            updated = update_task_safe(tb_id, status=status)
    else:
        updated = update_task_safe(tb_id, status=status)

    if updated is not None:
        _task_cache.set(tb_id, updated)


class _Cache:
    def __init__(self, maxsize=128):
        self.cache = collections.OrderedDict()
        self.maxsize = maxsize

    def set(self, key, value):
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def get(self, key):
        return self.cache.get(key)

    def unset(self, key):
        self.cache.pop(key, None)


_task_cache = _Cache()


def _safe_get_task(task_id):
    cached = _task_cache.get(task_id)
    if cached is not None:
        return cached
    try:
        task = get_task(task_id)
    except Exception as e:
        log.warning("Error fetching task '%s': %s", task_id, e)
        return None
    _task_cache.set(task_id, task)
    return task


def _wrap_defer(task):
    """Wrap ``task.defer`` and ``task.defer_async`` so they create a TaskBadger
    task in PENDING state and inject its id into the job's task_kwargs.

    Not idempotent on its own — the caller (``_instrument_task``) gates this
    via ``_INSTRUMENTED_ATTR`` so each task is wrapped at most once.
    """
    original_defer = task.defer
    original_defer_async = task.defer_async

    @functools.wraps(original_defer)
    def defer(**kwargs):
        kwargs = _maybe_create_pending(task, kwargs)
        return original_defer(**kwargs)

    @functools.wraps(original_defer_async)
    async def defer_async(**kwargs):
        kwargs = _maybe_create_pending(task, kwargs)
        return await original_defer_async(**kwargs)

    task.defer = defer
    task.defer_async = defer_async


def _maybe_create_pending(task, kwargs):
    """Decide whether to track this defer, and if so create the TaskBadger
    task and inject its id into ``kwargs``. Always returns the kwargs dict."""
    if not Badger.is_configured():
        return kwargs

    system = getattr(task, "_taskbadger_system", None)
    manual = getattr(task, _MANUAL_ATTR, False)
    auto = bool(system) and system.track_task(task.name)
    if not manual and not auto:
        return kwargs

    opts = dict(getattr(task, _OPTS_ATTR, {}) or {})
    name = opts.pop("name", None) or task.name
    create_kwargs = {"status": StatusEnum.PENDING}
    for key in ("value_max", "tags"):
        if key in opts and opts[key] is not None:
            create_kwargs[key] = opts[key]
    user_data = opts.get("data")
    if user_data:
        create_kwargs["data"] = dict(user_data)

    tb_task = create_task_safe(name, **create_kwargs)
    if tb_task is None:
        return kwargs

    new_kwargs = dict(kwargs)
    new_kwargs[TB_TASK_ID_KWARG] = tb_task.id
    return new_kwargs


_TRACK_OPT_KEYS = ("name", "value_max", "tags", "data", "record_task_args")


def track(original_task=None, **opts):
    """Opt a Procrastinate task into TaskBadger tracking.

    Usage:

        @track
        @app.task(...)
        def my_task(...): ...

        @track(name="custom", value_max=100, tags={"env": "prod"})
        @app.task(...)
        async def big_job(...): ...

    Accepted keyword options (all optional):
        name: TaskBadger task name (defaults to the Procrastinate task's name).
        value_max: Maximum value for the TaskBadger task.
        tags: Dict of tags applied to the TaskBadger task.
        data: Dict of initial data merged into the TaskBadger task.
        record_task_args: If True, serialize the Procrastinate job kwargs and
            store them under ``data["procrastinate_task_kwargs"]``. Defaults to
            ``None`` meaning "inherit from system integration if any, else False".
    """
    unknown = set(opts) - set(_TRACK_OPT_KEYS)
    if unknown:
        raise TypeError(f"track() got unexpected keyword arguments: {sorted(unknown)}")

    def wrap(task):
        _instrument_task(task, system=None, manual=True, opts=opts)
        return task

    if original_task is None:
        return wrap
    return wrap(original_task)


def current_task():
    """Return the TaskBadger Task for the currently-running Procrastinate job.

    Returns ``None`` outside of a tracked task or if the task can't be fetched.
    Result is cached for the lifetime of the worker process via an LRU.
    """
    tb_id = _current_tb_task_id.get()
    if tb_id is None:
        return None
    return _safe_get_task(tb_id)
