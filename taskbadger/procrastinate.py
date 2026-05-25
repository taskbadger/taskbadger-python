"""TaskBadger integration for the Procrastinate task queue.

This module is opt-in. Users install Procrastinate themselves (or via the
``taskbadger[procrastinate]`` extra) and import from here.

Public API:
    - ``track``: decorator to opt a single task into TaskBadger tracking.
    - ``current_task()``: accessor for the TaskBadger task associated with the
      currently-running Procrastinate job (returns ``None`` if not tracked).
"""

from __future__ import annotations

import functools
import inspect
import logging
from contextvars import ContextVar

from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import update_task_safe
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

    task.func = wrapped
    setattr(task, _INSTRUMENTED_ATTR, True)
    setattr(task, "_taskbadger_system", system)


def _update_status(tb_id, status, exception=None):
    """Update the TaskBadger task to ``status``. Skips if already terminal."""
    if not Badger.is_configured():
        return

    if exception is not None or status in TERMINAL_STATES:
        try:
            current = get_task(tb_id)
        except Exception as e:
            log.warning("Error fetching task '%s': %s", tb_id, e)
            current = None
        if current is not None and current.status in TERMINAL_STATES:
            return
        data = None
        if exception is not None and current is not None:
            data = DefaultMergeStrategy().merge(current.data, {"exception": str(exception)})
        if data:
            update_task_safe(tb_id, status=status, data=data)
        else:
            update_task_safe(tb_id, status=status)
    else:
        update_task_safe(tb_id, status=status)
