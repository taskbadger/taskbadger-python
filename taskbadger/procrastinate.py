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
import json
import logging
from contextvars import ContextVar

from ._integrations import TERMINAL_STATES, safe_get_task, task_cache
from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy

log = logging.getLogger("taskbadger")

# Reserved key used to smuggle the TaskBadger task id through Procrastinate's
# task_kwargs from the deferring process to the worker. Stripped before the
# user function is called.
TB_TASK_ID_KWARG = "__taskbadger_task_id__"

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

    # pass_context=True works transparently: Procrastinate passes the context
    # object as the first positional arg; our *args/**kwargs wrapper forwards it.
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
        task_cache.unset(tb_id)
        current = safe_get_task(tb_id)
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
        task_cache.set(tb_id, updated)


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


def _create_pending_task(task, task_kwargs, queue=None):
    """Create a PENDING TaskBadger task for ``task`` if it should be tracked.

    Returns the created TaskBadger task, or ``None`` if Badger isn't
    configured, the task isn't tracked (neither manual nor auto), or the
    create call failed. ``task_kwargs`` is used only for the
    ``record_task_args`` data capture. ``queue`` overrides the queue name
    recorded on the TaskBadger task (defaults to the task's own queue).
    """
    if not Badger.is_configured():
        return None

    system = getattr(task, "_taskbadger_system", None)
    manual = getattr(task, _MANUAL_ATTR, False)
    auto = bool(system) and system.track_task(task.name)
    if not manual and not auto:
        return None

    opts = dict(getattr(task, _OPTS_ATTR, {}) or {})
    name = opts.pop("name", None) or task.name
    create_kwargs = {"status": StatusEnum.PENDING}
    queue = queue or getattr(task, "queue", None)
    if queue is not None:
        create_kwargs["queue"] = queue
    for key in ("value_max", "tags"):
        if key in opts and opts[key] is not None:
            create_kwargs[key] = opts[key]

    data = dict(opts.get("data") or {})

    record_args = opts.get("record_task_args")
    if record_args is None:
        record_args = bool(system) and system.record_task_args
    if record_args:
        data["procrastinate_task_kwargs"] = _serialize_kwargs(task_kwargs)

    if data:
        create_kwargs["data"] = data

    return create_task_safe(name, **create_kwargs)


def _maybe_create_pending(task, kwargs):
    """Decide whether to track this defer, and if so create the TaskBadger
    task and inject its id into ``kwargs``. Always returns the kwargs dict."""
    tb_task = _create_pending_task(task, kwargs)
    if tb_task is None:
        return kwargs

    new_kwargs = dict(kwargs)
    new_kwargs[TB_TASK_ID_KWARG] = tb_task.id
    return new_kwargs


def _serialize_kwargs(kwargs):
    """Return a JSON-roundtrippable copy of the defer kwargs.

    Procrastinate already requires kwargs be JSON-serializable, so a json
    dumps/loads roundtrip is safe. Non-serializable values are dropped with
    a warning."""
    try:
        return json.loads(json.dumps(kwargs))
    except (TypeError, ValueError) as e:
        log.warning("Error serializing task arguments: %s", e)
        return {}


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
    return safe_get_task(tb_id)


def _patch_job_manager(app, system):
    """Patch ``app.job_manager.defer_periodic_job`` so periodic tasks are tracked.

    Procrastinate's ``PeriodicDeferrer`` enqueues jobs by calling
    ``job_manager.defer_periodic_job(job=..., ...)`` directly, bypassing
    ``task.defer``/``defer_async``. Without this hook, ``@app.periodic`` tasks
    would never get a PENDING TaskBadger task created at enqueue time.

    Idempotent: a second call updates the system reference but doesn't
    re-wrap.
    """
    jm = app.job_manager
    if not getattr(jm, "_taskbadger_original_defer_periodic_job", None):
        original = jm.defer_periodic_job
        jm._taskbadger_original_defer_periodic_job = original

        @functools.wraps(original)
        async def patched(*, job, periodic_id, defer_timestamp):
            task = app.tasks.get(job.task_name)
            if task is not None:
                tb_task = _create_pending_task(task, job.task_kwargs, queue=job.queue)
                if tb_task is not None:
                    new_kwargs = {**job.task_kwargs, TB_TASK_ID_KWARG: tb_task.id}
                    job = job.evolve(task_kwargs=new_kwargs)
            return await jm._taskbadger_original_defer_periodic_job(
                job=job, periodic_id=periodic_id, defer_timestamp=defer_timestamp
            )

        jm.defer_periodic_job = patched


def _patch_app_task(app, system):
    """Replace ``app.task`` with a wrapper that instruments newly-registered
    tasks under the supplied ``system``. Idempotent — a second call replaces
    the wrapper but keeps the same original task method."""
    original = getattr(app, "_taskbadger_original_task", None) or app.task
    if not getattr(app, "_taskbadger_original_task", None):
        app._taskbadger_original_task = original

    @functools.wraps(original)
    def patched(*args, **kwargs):
        task = original(*args, **kwargs)
        # ``original`` may return the Task directly or a decorator depending on
        # call form. Procrastinate's ``app.task`` always returns a decorator
        # when called with arguments and the Task when called bare.
        if callable(task) and not hasattr(task, "name"):
            # decorator form: wrap the returned decorator
            inner_decorator = task

            @functools.wraps(inner_decorator)
            def outer(func):
                t = inner_decorator(func)
                _instrument_task(t, system=system)
                return t

            return outer
        _instrument_task(task, system=system)
        return task

    app.task = patched
