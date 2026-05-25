# Procrastinate Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class TaskBadger tracking support for the [Procrastinate](https://procrastinate.readthedocs.io/) task queue, paralleling the existing Celery integration with a `@track` decorator, a `ProcrastinateSystemIntegration`, and full lifecycle tracking (PENDING → PROCESSING → SUCCESS/ERROR).

**Architecture:** Per-task wrapping that smuggles the TaskBadger task id through Procrastinate's `task_kwargs` under a reserved key, strips it before invoking the user function, and exposes the current task through a `ContextVar`. A system integration installs itself on a Procrastinate `App`, wrapping existing tasks and monkey-patching `app.task` so future tasks are wrapped on registration.

**Tech Stack:** Python 3.10+, `procrastinate >= 3.0` (new optional extra), existing TaskBadger SDK primitives (`create_task_safe`, `update_task_safe`, `get_task`, `Badger`, `Session`, `DefaultMergeStrategy`).

**Spec:** `docs/superpowers/specs/2026-05-25-procrastinate-integration-design.md`

---

## File map

- Create: `taskbadger/procrastinate.py` — public API: `track` decorator, `current_task()`, internal wrap helpers.
- Create: `taskbadger/systems/procrastinate.py` — `ProcrastinateSystemIntegration`.
- Create: `tests/test_procrastinate.py` — unit tests using `InMemoryConnector`.
- Create: `tests/test_procrastinate_system_integration.py` — system integration unit tests.
- Create: `integration_tests/test_procrastinate.py` — real Postgres + Procrastinate.
- Modify: `pyproject.toml` — add `procrastinate` optional extra and dev dep.
- Modify: `README.md` — add a Procrastinate section paralleling Celery.

---

## Task 1: Scaffolding — optional dep and empty modules

**Files:**
- Modify: `pyproject.toml`
- Create: `taskbadger/procrastinate.py`
- Create: `taskbadger/systems/procrastinate.py`

- [ ] **Step 1: Add `procrastinate` to optional and dev dependencies**

Edit `pyproject.toml`. Under `[project.optional-dependencies]` add a new extra after the existing `cli` entry:

```toml
procrastinate = [
    "procrastinate>=3.0",
]
```

Under `[dependency-groups].dev` add `"procrastinate"` to the list (place it alphabetically, e.g., after `"pre-commit"` or wherever fits the existing ordering).

- [ ] **Step 2: Sync the lockfile**

Run: `uv sync --frozen --all-extras 2>&1 | tail -20`

If `--frozen` fails because `procrastinate` is new and not yet pinned, run `uv sync --all-extras` (without `--frozen`) and confirm `uv.lock` is updated.

Expected: `procrastinate` installed under the dev group; no other dependency changes.

- [ ] **Step 3: Create `taskbadger/procrastinate.py` skeleton**

```python
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
import json
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
```

All imports stay at module top; later tasks add functions below this header without touching the imports.

- [ ] **Step 4: Create `taskbadger/systems/procrastinate.py` skeleton**

```python
"""ProcrastinateSystemIntegration — auto-track tasks on a Procrastinate App."""

from __future__ import annotations

from taskbadger.systems import System


class ProcrastinateSystemIntegration(System):
    identifier = "procrastinate"
```

- [ ] **Step 5: Verify both modules import cleanly**

Run: `uv run python -c "import taskbadger.procrastinate; import taskbadger.systems.procrastinate; print('ok')"`

Expected output: `ok`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock taskbadger/procrastinate.py taskbadger/systems/procrastinate.py
git commit -m "feat(procrastinate): add optional dependency and module skeletons"
```

---

## Task 2: Per-task wrapper — worker-side lifecycle (no defer wrapping yet)

This task wraps the task function so that *if* `__taskbadger_task_id__` is present in kwargs, the worker side updates the TB task. Defer-side injection comes in Task 3.

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Create: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing test for sync task worker-side lifecycle**

Create `tests/test_procrastinate.py`:

```python
import logging
from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

from taskbadger import StatusEnum
from taskbadger.procrastinate import TB_TASK_ID_KWARG, _instrument_task
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


@pytest.fixture
def app():
    in_memory = testing.InMemoryConnector()
    app = procrastinate.App(connector=in_memory)
    with app.open():
        yield app


@pytest.mark.usefixtures("_bind_settings")
def test_worker_updates_task_sync(app):
    @app.task(name="add")
    def add(a, b):
        return a + b

    _instrument_task(add, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING)
        add.func(a=2, b=3, **{TB_TASK_ID_KWARG: "tb-123"})

    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]
    # The reserved key must not appear in the calls (it's stripped before user fn)
    assert all(TB_TASK_ID_KWARG not in c.kwargs for c in update.call_args_list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_procrastinate.py::test_worker_updates_task_sync -v`

Expected: FAIL with `ImportError` or `AttributeError` for `_instrument_task` (not defined yet).

- [ ] **Step 3: Implement the worker-side wrapper in `taskbadger/procrastinate.py`**

Append the following functions to the module (imports are already at the top from Task 1):

```python
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
        update_task_safe(tb_id, status=status, data=data) if data else update_task_safe(tb_id, status=status)
    else:
        update_task_safe(tb_id, status=status)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_procrastinate.py::test_worker_updates_task_sync -v`

Expected: PASS.

- [ ] **Step 5: Add the async-task counterpart test**

Append to `tests/test_procrastinate.py`:

```python
import asyncio


@pytest.mark.usefixtures("_bind_settings")
def test_worker_updates_task_async(app):
    @app.task(name="add_async")
    async def add_async(a, b):
        return a + b

    _instrument_task(add_async, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING)
        result = asyncio.run(add_async.func(a=2, b=3, **{TB_TASK_ID_KWARG: "tb-456"}))

    assert result == 5
    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]
```

- [ ] **Step 6: Run async test, expect pass**

Run: `uv run pytest tests/test_procrastinate.py::test_worker_updates_task_async -v`

Expected: PASS.

- [ ] **Step 7: Add the error test**

Append to `tests/test_procrastinate.py`:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_worker_marks_error(app):
    @app.task(name="boom")
    def boom():
        raise ValueError("nope")

    _instrument_task(boom, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING, data={"x": 1})
        with pytest.raises(ValueError):
            boom.func(**{TB_TASK_ID_KWARG: "tb-789"})

    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.ERROR]
    err_call = update.call_args_list[-1]
    assert err_call.kwargs["data"] == {"x": 1, "exception": "nope"}
```

- [ ] **Step 8: Run the error test, expect pass**

Run: `uv run pytest tests/test_procrastinate.py -v`

Expected: 3 PASS.

- [ ] **Step 9: Add the "no id present" test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_worker_no_id_runs_clean(app):
    @app.task(name="add2")
    def add2(a, b):
        return a + b

    _instrument_task(add2, system=None, manual=True)

    with mock.patch("taskbadger.procrastinate.update_task_safe") as update:
        result = add2.func(a=1, b=2)

    assert result == 3
    update.assert_not_called()
```

- [ ] **Step 10: Run all tests, then commit**

Run: `uv run pytest tests/test_procrastinate.py -v`

Expected: 4 PASS.

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): worker-side task wrapper with sync/async support"
```

---

## Task 3: Defer-time wrapping — create PENDING task and inject id

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Modify: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing defer-time test**

Append to `tests/test_procrastinate.py`:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_defer_creates_pending_task_and_injects_id(app):
    @app.task(name="add3")
    def add3(a, b):
        return a + b

    _instrument_task(add3, system=None, manual=True)

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        add3.defer(a=1, b=2)

    create.assert_called_once()
    assert create.call_args.args == ("add3",)
    assert create.call_args.kwargs == {"status": StatusEnum.PENDING}

    # The injected id should appear in the Procrastinate job's task_kwargs.
    jobs = app.connector.jobs
    assert len(jobs) == 1
    assert jobs[0]["task_kwargs"][TB_TASK_ID_KWARG] == tb.id
```

- [ ] **Step 2: Run test, expect fail**

Run: `uv run pytest tests/test_procrastinate.py::test_defer_creates_pending_task_and_injects_id -v`

Expected: FAIL — `task_kwargs` does not contain the reserved key (defer not wrapped yet).

- [ ] **Step 3: Add `safe_get_task` helper**

`create_task_safe` and `collections` are already imported at the module top from Task 1. After the `_update_status` function add:

```python
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
```

Replace the `get_task(tb_id)` call inside `_update_status` with `_safe_get_task(tb_id)` so the error-path lookup is cached:

```python
def _update_status(tb_id, status, exception=None):
    if not Badger.is_configured():
        return

    if exception is not None or status in TERMINAL_STATES:
        current = _safe_get_task(tb_id)
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
```

- [ ] **Step 4: Implement defer-wrapping in `_instrument_task`**

Just before the final `task.func = wrapped` / `setattr` block in `_instrument_task`, add:

```python
    _wrap_defer(task)
```

Then add this new function below `_instrument_task`:

```python
def _wrap_defer(task):
    """Wrap ``task.defer`` and ``task.defer_async`` so they create a TaskBadger
    task in PENDING state and inject its id into the job's task_kwargs.

    The original defer methods are stashed on the task to keep the wrap
    idempotent (a second call replaces nothing because the marker is set)."""
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
```

- [ ] **Step 5: Re-run the defer test, expect pass**

Run: `uv run pytest tests/test_procrastinate.py::test_defer_creates_pending_task_and_injects_id -v`

Expected: PASS.

- [ ] **Step 6: Add a defer-when-not-configured test**

Append:

```python
def test_defer_no_taskbadger_when_unconfigured(app):
    @app.task(name="add4")
    def add4(a, b):
        return a + b

    _instrument_task(add4, system=None, manual=True)

    # Badger is not configured (no _bind_settings fixture).
    with mock.patch("taskbadger.procrastinate.create_task_safe") as create:
        add4.defer(a=1, b=2)

    create.assert_not_called()
    jobs = app.connector.jobs
    assert TB_TASK_ID_KWARG not in jobs[0]["task_kwargs"]
```

- [ ] **Step 7: Add an async-defer test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_defer_async_injects_id(app):
    @app.task(name="add5")
    async def add5(a, b):
        return a + b

    _instrument_task(add5, system=None, manual=True)

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb):
        asyncio.run(add5.defer_async(a=1, b=2))

    jobs = app.connector.jobs
    assert jobs[0]["task_kwargs"][TB_TASK_ID_KWARG] == tb.id
```

- [ ] **Step 8: Add an end-to-end test (defer + run worker)**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_end_to_end_via_worker(app):
    @app.task(name="add6")
    def add6(a, b):
        return a + b

    _instrument_task(add6, system=None, manual=True)

    tb = task_for_test()
    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(id=tb.id, status=StatusEnum.PROCESSING)
        add6.defer(a=2, b=3)
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    create.assert_called_once()
    statuses = [c.kwargs["status"] for c in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]
```

- [ ] **Step 9: Run all tests in the file**

Run: `uv run pytest tests/test_procrastinate.py -v`

Expected: 7 PASS.

- [ ] **Step 10: Commit**

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): defer-time task creation with id injection"
```

---

## Task 4: `@track` decorator — public API for opt-in tracking

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Modify: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing test for the bare decorator**

Append to `tests/test_procrastinate.py`:

```python
from taskbadger.procrastinate import track


@pytest.mark.usefixtures("_bind_settings")
def test_track_bare_form(app):
    @track
    @app.task(name="bare")
    def bare(a):
        return a

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb):
        bare.defer(a=1)

    assert getattr(bare, "_taskbadger_manual") is True
    assert app.connector.jobs[0]["task_kwargs"][TB_TASK_ID_KWARG] == tb.id


@pytest.mark.usefixtures("_bind_settings")
def test_track_parameterized(app):
    @track(name="custom", value_max=10, tags={"env": "test"}, data={"k": "v"})
    @app.task(name="raw_name")
    def raw(a):
        return a

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        raw.defer(a=1)

    create.assert_called_once()
    assert create.call_args.args == ("custom",)
    assert create.call_args.kwargs == {
        "status": StatusEnum.PENDING,
        "value_max": 10,
        "tags": {"env": "test"},
        "data": {"k": "v"},
    }
```

- [ ] **Step 2: Run tests, expect ImportError on `track`**

Run: `uv run pytest tests/test_procrastinate.py::test_track_bare_form -v`

Expected: FAIL — `track` not yet defined.

- [ ] **Step 3: Implement `track` in `taskbadger/procrastinate.py`**

Append at the bottom of the module:

```python
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
```

- [ ] **Step 4: Run the new tests, expect pass**

Run: `uv run pytest tests/test_procrastinate.py::test_track_bare_form tests/test_procrastinate.py::test_track_parameterized -v`

Expected: 2 PASS.

- [ ] **Step 5: Add idempotency test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_track_idempotent(app):
    @track
    @track
    @app.task(name="dup")
    def dup(a):
        return a

    # Two @track applications must not double-wrap; defer once still creates one
    # PENDING task and injects one id.
    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        dup.defer(a=1)
    assert create.call_count == 1
    kwargs_in_job = app.connector.jobs[0]["task_kwargs"]
    # Reserved key appears exactly once
    assert list(kwargs_in_job).count(TB_TASK_ID_KWARG) == 1
```

- [ ] **Step 6: Run idempotency test**

Run: `uv run pytest tests/test_procrastinate.py::test_track_idempotent -v`

Expected: PASS.

- [ ] **Step 7: Add the "unknown opt raises" test**

Append:

```python
def test_track_unknown_opt_raises(app):
    @app.task(name="bad")
    def bad():
        pass

    with pytest.raises(TypeError, match="unexpected keyword"):
        track(name="x", does_not_exist=True)(bad)
```

- [ ] **Step 8: Run all file tests, then commit**

Run: `uv run pytest tests/test_procrastinate.py -v`

Expected: all PASS (10 tests).

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): @track decorator with bare and parameterized forms"
```

---

## Task 5: `current_task()` accessor via ContextVar

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Modify: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_procrastinate.py`:

```python
from taskbadger.procrastinate import current_task


@pytest.mark.usefixtures("_bind_settings")
def test_current_task_inside_body(app):
    captured = {}

    @track
    @app.task(name="capture")
    def capture():
        captured["task"] = current_task()

    tb = task_for_test()
    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb),
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.procrastinate.get_task", return_value=tb),
    ):
        capture.defer()
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    assert captured["task"] is not None
    assert captured["task"].id == tb.id


def test_current_task_outside_returns_none():
    assert current_task() is None
```

- [ ] **Step 2: Run tests, expect fail (`current_task` import)**

Run: `uv run pytest tests/test_procrastinate.py::test_current_task_inside_body tests/test_procrastinate.py::test_current_task_outside_returns_none -v`

Expected: FAIL — `current_task` not defined.

- [ ] **Step 3: Implement `current_task` in `taskbadger/procrastinate.py`**

Append:

```python
def current_task():
    """Return the TaskBadger Task for the currently-running Procrastinate job.

    Returns ``None`` outside of a tracked task or if the task can't be fetched.
    Result is cached for the lifetime of the worker process via an LRU.
    """
    tb_id = _current_tb_task_id.get()
    if tb_id is None:
        return None
    return _safe_get_task(tb_id)
```

- [ ] **Step 4: Run tests, expect pass**

Run: `uv run pytest tests/test_procrastinate.py::test_current_task_inside_body tests/test_procrastinate.py::test_current_task_outside_returns_none -v`

Expected: 2 PASS.

- [ ] **Step 5: Add "terminal state in body" test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_user_set_terminal_state_not_overwritten(app):
    @track
    @app.task(name="self_complete")
    def self_complete():
        pass

    tb_pending = task_for_test(status=StatusEnum.PENDING)
    tb_done = task_for_test(id=tb_pending.id, status=StatusEnum.SUCCESS)

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb_pending),
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task", return_value=tb_done),
    ):
        self_complete.defer()
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    # The wrapper's post-call SUCCESS update is skipped because the cached
    # task is already SUCCESS. PROCESSING update is still allowed (early path).
    statuses = [c.kwargs["status"] for c in update.call_args_list]
    assert StatusEnum.PROCESSING in statuses
    # Last attempted SUCCESS call should be suppressed
    assert statuses.count(StatusEnum.SUCCESS) == 0
```

- [ ] **Step 6: Run terminal-state test**

Run: `uv run pytest tests/test_procrastinate.py::test_user_set_terminal_state_not_overwritten -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): current_task() accessor via ContextVar"
```

---

## Task 6: `record_task_args` — store defer kwargs in TB task data

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Modify: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_record_task_args_stores_kwargs(app):
    @track(record_task_args=True, data={"existing": 1})
    @app.task(name="recorder")
    def recorder(a, b):
        return a + b

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        recorder.defer(a=5, b=6)

    assert create.call_args.kwargs["data"] == {
        "existing": 1,
        "procrastinate_task_kwargs": {"a": 5, "b": 6},
    }
```

- [ ] **Step 2: Run test, expect fail**

Run: `uv run pytest tests/test_procrastinate.py::test_record_task_args_stores_kwargs -v`

Expected: FAIL — `procrastinate_task_kwargs` not present in `data`.

- [ ] **Step 3: Implement record_task_args in `_maybe_create_pending`**

Edit `_maybe_create_pending` in `taskbadger/procrastinate.py`. Replace the body of the function with:

```python
def _maybe_create_pending(task, kwargs):
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

    data = dict(opts.get("data") or {})

    record_args = opts.get("record_task_args")
    if record_args is None:
        record_args = bool(system) and system.record_task_args
    if record_args:
        data["procrastinate_task_kwargs"] = _serialize_kwargs(kwargs)

    if data:
        create_kwargs["data"] = data

    tb_task = create_task_safe(name, **create_kwargs)
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
```

(`json` is already imported at the top from Task 1.)

- [ ] **Step 4: Run test, expect pass**

Run: `uv run pytest tests/test_procrastinate.py::test_record_task_args_stores_kwargs -v`

Expected: PASS.

- [ ] **Step 5: Run full file, then commit**

Run: `uv run pytest tests/test_procrastinate.py -v`

Expected: all PASS.

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): record_task_args stores defer kwargs in task data"
```

---

## Task 7: `pass_context=True` compatibility

**Files:**
- Modify: `taskbadger/procrastinate.py`
- Modify: `tests/test_procrastinate.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_pass_context_forwards_context(app):
    seen = {}

    @track
    @app.task(name="ctx_task", pass_context=True)
    def ctx_task(context, a):
        seen["context"] = context
        seen["a"] = a

    tb = task_for_test()
    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb),
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.procrastinate.get_task", return_value=tb),
    ):
        ctx_task.defer(a=42)
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    assert seen["a"] == 42
    # Context object should be passed through unchanged
    assert seen["context"] is not None
    assert seen["context"].task is ctx_task
```

- [ ] **Step 2: Run test, expect fail**

Run: `uv run pytest tests/test_procrastinate.py::test_pass_context_forwards_context -v`

Expected: FAIL (depending on Procrastinate's behaviour — the wrapped function may not accept a positional context arg, OR the wrapper may strip it as if it were a kwarg).

Note: Procrastinate passes the context as the first positional argument to the task function when `pass_context=True`. Our existing wrapper accepts `*args, **kwargs`, so the context is forwarded transparently — verify if the test actually fails before assuming work is needed.

- [ ] **Step 3: If the test passes already, document and skip implementation**

If Step 2 PASSED, the existing wrapper already handles context correctly (because it forwards `*args, **kwargs` to the original function). Add a one-line comment in `_instrument_task` above the `if is_async:` branch:

```python
    # pass_context=True works transparently: Procrastinate passes the context
    # object as the first positional arg; our *args/**kwargs wrapper forwards it.
```

If Step 2 FAILED, investigate what Procrastinate does — likely it inspects the task function's signature to decide whether to pass context. We may need to copy the signature from the original function onto the wrapper. Use `functools.wraps` (already applied) — if signature inspection still fails, attach `__wrapped__` explicitly or replicate the original signature via `inspect.Signature`.

- [ ] **Step 4: Run the test until pass**

Run: `uv run pytest tests/test_procrastinate.py::test_pass_context_forwards_context -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate.py
git commit -m "feat(procrastinate): verify pass_context=True works with task wrapper"
```

---

## Task 8: `ProcrastinateSystemIntegration` — auto-track and includes/excludes

**Files:**
- Modify: `taskbadger/systems/procrastinate.py`
- Create: `tests/test_procrastinate_system_integration.py`

- [ ] **Step 1: Write failing tests for include/exclude regex**

Create `tests/test_procrastinate_system_integration.py`:

```python
import procrastinate
import pytest
from procrastinate import testing

from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration


@pytest.fixture
def app():
    in_memory = testing.InMemoryConnector()
    app = procrastinate.App(connector=in_memory)
    with app.open():
        yield app


@pytest.mark.parametrize(
    ("include", "exclude", "expected"),
    [
        (None, None, True),
        (["myapp.tasks.export_data"], None, True),
        ([".*export_data"], [], True),
        ([".*export_da"], [], False),
        (["myapp.tasks.export_data"], ["myapp.tasks.export_data"], False),
        ([".*"], ["myapp.tasks.export_data"], False),
        ([".*"], [".*tasks.*"], False),
    ],
)
def test_task_name_matching(app, include, exclude, expected):
    integration = ProcrastinateSystemIntegration(
        app=app, includes=include, excludes=exclude
    )
    assert integration.track_task("myapp.tasks.export_data") is expected


def test_auto_track_off_returns_false(app):
    integration = ProcrastinateSystemIntegration(app=app, auto_track_tasks=False)
    assert integration.track_task("anything") is False
```

- [ ] **Step 2: Run tests, expect fail**

Run: `uv run pytest tests/test_procrastinate_system_integration.py -v`

Expected: FAIL — `ProcrastinateSystemIntegration` is a stub with no `__init__` or `track_task`.

- [ ] **Step 3: Implement `ProcrastinateSystemIntegration`**

Replace the contents of `taskbadger/systems/procrastinate.py`:

```python
"""ProcrastinateSystemIntegration — auto-track tasks on a Procrastinate App."""

from __future__ import annotations

import re

from taskbadger.procrastinate import _instrument_task, _patch_app_task
from taskbadger.systems import System


class ProcrastinateSystemIntegration(System):
    identifier = "procrastinate"

    def __init__(
        self,
        app,
        auto_track_tasks=True,
        includes=None,
        excludes=None,
        record_task_args=False,
    ):
        """
        Args:
            app: The ``procrastinate.App`` instance to instrument.
            auto_track_tasks: Track all tasks regardless of whether they use
                the ``@taskbadger.procrastinate.track`` decorator.
            includes: List of task names to include in auto-tracking. Each
                entry can be a full name or a regex (matched with
                ``re.fullmatch``).
            excludes: List of task names to exclude. Same semantics as
                ``includes``. Exclusions take precedence.
            record_task_args: Record the task's defer kwargs into the
                TaskBadger task's ``data`` under ``procrastinate_task_kwargs``.
        """
        self.app = app
        self.auto_track_tasks = auto_track_tasks
        self.includes = includes
        self.excludes = excludes
        self.record_task_args = record_task_args

        for task in list(app.tasks.values()):
            _instrument_task(task, system=self)
        _patch_app_task(app, system=self)

    def track_task(self, task_name):
        if not self.auto_track_tasks:
            return False

        if self.excludes:
            for exclude in self.excludes:
                if re.fullmatch(exclude, task_name):
                    return False

        if self.includes:
            for include in self.includes:
                if re.fullmatch(include, task_name):
                    break
            else:
                return False

        return True
```

- [ ] **Step 4: Add `_patch_app_task` to `taskbadger/procrastinate.py`**

Append:

```python
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
```

- [ ] **Step 5: Run the system-integration tests**

Run: `uv run pytest tests/test_procrastinate_system_integration.py -v`

Expected: PASS for all `track_task` parametrize cases and `auto_track_off`.

- [ ] **Step 6: Add wrapping test for existing tasks**

Append to `tests/test_procrastinate_system_integration.py`:

```python
from unittest import mock

from taskbadger import StatusEnum
from taskbadger.procrastinate import TB_TASK_ID_KWARG, _INSTRUMENTED_ATTR
from tests.utils import task_for_test


def test_wraps_existing_tasks(app):
    @app.task(name="pre_existing")
    def pre_existing(a):
        return a

    assert not getattr(pre_existing, _INSTRUMENTED_ATTR, False)
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)
    assert getattr(pre_existing, _INSTRUMENTED_ATTR) is True


@pytest.mark.usefixtures("_bind_settings")
def test_auto_track_creates_pending(app):
    @app.task(name="auto_target")
    def auto_target(a):
        return a

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    tb = task_for_test()
    with mock.patch(
        "taskbadger.procrastinate.create_task_safe", return_value=tb
    ) as create:
        auto_target.defer(a=1)

    create.assert_called_once()
    assert app.connector.jobs[0]["task_kwargs"][TB_TASK_ID_KWARG] == tb.id


@pytest.mark.usefixtures("_bind_settings")
def test_auto_track_excludes_skip(app):
    @app.task(name="myapp.cleanup.flush")
    def flush():
        pass

    ProcrastinateSystemIntegration(
        app=app, auto_track_tasks=True, excludes=[r"myapp\.cleanup\..*"]
    )

    with mock.patch("taskbadger.procrastinate.create_task_safe") as create:
        flush.defer()

    create.assert_not_called()
```

- [ ] **Step 7: Run the new tests**

Run: `uv run pytest tests/test_procrastinate_system_integration.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add taskbadger/systems/procrastinate.py taskbadger/procrastinate.py tests/test_procrastinate_system_integration.py
git commit -m "feat(procrastinate): ProcrastinateSystemIntegration with auto-track"
```

---

## Task 9: System integration auto-wraps new tasks (post-init registrations)

**Files:**
- Modify: `tests/test_procrastinate_system_integration.py`
- Modify: `taskbadger/procrastinate.py` (only if Task 8's `_patch_app_task` needs fixing)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_procrastinate_system_integration.py`:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_wraps_tasks_registered_after_init(app):
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    @app.task(name="late")
    def late(a):
        return a

    assert getattr(late, _INSTRUMENTED_ATTR) is True

    tb = task_for_test()
    with mock.patch(
        "taskbadger.procrastinate.create_task_safe", return_value=tb
    ) as create:
        late.defer(a=1)

    create.assert_called_once()
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_procrastinate_system_integration.py::test_wraps_tasks_registered_after_init -v`

If it PASSES, the implementation from Task 8 is complete — move to Step 4.

If it FAILS, the `_patch_app_task` wrapper in Task 8 needs to be revised based on the actual return shape of `app.task`. Inspect with a small repl:

```bash
uv run python -c "
import procrastinate
app = procrastinate.App(connector=procrastinate.testing.InMemoryConnector())
print(type(app.task), type(app.task(name='x')))
"
```

Fix `_patch_app_task` so both `@app.task` (bare) and `@app.task(name='x')` (with args) get their returned task instrumented.

- [ ] **Step 3: Re-run until pass**

Run: `uv run pytest tests/test_procrastinate_system_integration.py::test_wraps_tasks_registered_after_init -v`

Expected: PASS.

- [ ] **Step 4: Add idempotency test for `@track` + system integration**

Append:

```python
@pytest.mark.usefixtures("_bind_settings")
def test_track_plus_auto_track_no_double_wrap(app):
    from taskbadger.procrastinate import track

    @track
    @app.task(name="manual_plus_auto")
    def both():
        pass

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    # _instrument_task is idempotent — system init must not re-wrap.
    tb = task_for_test()
    with mock.patch(
        "taskbadger.procrastinate.create_task_safe", return_value=tb
    ) as create:
        both.defer()

    assert create.call_count == 1
    kwargs = app.connector.jobs[0]["task_kwargs"]
    assert list(kwargs).count(TB_TASK_ID_KWARG) == 1
```

- [ ] **Step 5: Run all system-integration tests**

Run: `uv run pytest tests/test_procrastinate_system_integration.py -v`

Expected: all PASS.

- [ ] **Step 6: Run the full unit test suite**

Run: `uv run pytest -v`

Expected: no regressions in existing tests; all new tests pass.

- [ ] **Step 7: Commit**

```bash
git add taskbadger/procrastinate.py tests/test_procrastinate_system_integration.py
git commit -m "feat(procrastinate): auto-wrap tasks registered after system init"
```

---

## Task 10: Integration test against real Postgres

**Files:**
- Create: `integration_tests/test_procrastinate.py`

- [ ] **Step 1: Add a Postgres connection helper section to the test file**

Create `integration_tests/test_procrastinate.py`:

```python
"""Integration tests for the Procrastinate integration.

Requires a running Postgres instance reachable via the ``PROCRASTINATE_DSN``
env var (e.g. ``postgresql://postgres:postgres@localhost:5432/procrastinate``)
and valid TaskBadger creds in ``TASKBADGER_*``.

These tests are excluded from the default pytest run via ``norecursedirs`` in
pyproject.toml.
"""

import logging
import os
import random

import procrastinate
import pytest

import taskbadger
from taskbadger import StatusEnum
from taskbadger.procrastinate import current_task, track
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration


PROCRASTINATE_DSN = os.environ.get(
    "PROCRASTINATE_DSN",
    "postgresql://postgres:postgres@localhost:5432/procrastinate",
)


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    for when in ("call", "setup", "teardown"):
        errors = [r.getMessage() for r in caplog.get_records(when) if r.levelno == logging.ERROR]
        if errors:
            pytest.fail(f"log errors during '{when}': {errors}")


@pytest.fixture(scope="session")
def app():
    """A Procrastinate app pointed at a real Postgres instance with its schema applied."""
    conn = procrastinate.SyncPsycopgConnector(conninfo=PROCRASTINATE_DSN)
    app = procrastinate.App(connector=conn)
    with app.open():
        # Apply schema (idempotent — Procrastinate's apply_schema is safe to re-run).
        app.schema_manager.apply_schema()
        yield app
```

- [ ] **Step 2: Add a manually-tracked task test**

Append:

```python
def test_track_decorator(app):
    @track
    @app.task(name="add_manual", queue="taskbadger_int")
    def add_manual(a, b):
        tb = current_task()
        assert tb is not None
        tb.update(value=100, data={"result": a + b})
        return a + b

    a, b = random.randint(1, 1000), random.randint(1, 1000)
    job_id = add_manual.defer(a=a, b=b)
    app.run_worker(
        queues=["taskbadger_int"],
        wait=False,
        install_signal_handlers=False,
        listen_notify=False,
    )

    # The TB task id was stashed in the job kwargs at defer time. Read it back
    # from Procrastinate's connector to verify the final state.
    # (Job kwargs are stored in the procrastinate_jobs table.)
    with app.connector.get_sync_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT args FROM procrastinate_jobs WHERE id = %s", (job_id,)
            )
            row = cur.fetchone()
    args = row[0]
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
    assert fetched.value == 100
    assert fetched.data == {"result": a + b}
```

- [ ] **Step 3: Add an auto-tracked task test**

Append:

```python
def test_auto_track_via_system(app):
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    @app.task(name="add_auto", queue="taskbadger_int_auto")
    def add_auto(a, b):
        return a + b

    a, b = random.randint(1, 1000), random.randint(1, 1000)
    job_id = add_auto.defer(a=a, b=b)
    app.run_worker(
        queues=["taskbadger_int_auto"],
        wait=False,
        install_signal_handlers=False,
        listen_notify=False,
    )

    with app.connector.get_sync_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT args FROM procrastinate_jobs WHERE id = %s", (job_id,)
            )
            row = cur.fetchone()
    args = row[0]
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
```

- [ ] **Step 4: Add a `conftest.py` for integration tests (if missing) that initializes TaskBadger**

Check `integration_tests/__init__.py` or `conftest.py`. If TaskBadger is not initialized in the integration tests session, create `integration_tests/conftest.py`:

```python
import pytest

import taskbadger


@pytest.fixture(scope="session", autouse=True)
def _init_taskbadger():
    taskbadger.init(tags={"env": "integration"})
```

(`taskbadger.init` reads `TASKBADGER_*` env vars when args are not supplied.)

- [ ] **Step 5: Run the integration tests (requires Postgres + TB creds)**

Run: `uv run pytest integration_tests/test_procrastinate.py -vs`

Expected: 2 PASS. If the runtime environment doesn't have Postgres, skip this step and document the requirement.

- [ ] **Step 6: Commit**

```bash
git add integration_tests/test_procrastinate.py integration_tests/conftest.py
git commit -m "test(procrastinate): integration tests against real Postgres"
```

---

## Task 11: README documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the Celery section in `README.md`**

Run: `grep -n -i "celery" /home/skelly/src/taskbadger-python/README.md | head`

Identify the heading and surrounding section.

- [ ] **Step 2: Add a Procrastinate section paralleling Celery**

Insert a new section directly after the Celery section. Use this content as a starting point — adapt heading levels and prose voice to match the file:

````markdown
### Procrastinate

The SDK includes optional support for the [Procrastinate](https://procrastinate.readthedocs.io/)
task queue.

Install with the extra:

```bash
pip install taskbadger[procrastinate]
```

Opt a single task into tracking with the `track` decorator:

```python
import procrastinate
from taskbadger.procrastinate import track, current_task

app = procrastinate.App(connector=...)

@track
@app.task(queue="default")
async def add(a, b):
    return a + b

@track(name="report", value_max=100, tags={"env": "prod"})
@app.task
async def report(rows):
    tb = current_task()
    for i, row in enumerate(rows):
        await process(row)
        if i % 10 == 0:
            tb.update(value=i, value_max=len(rows))
```

To auto-track every task on an App, register the system integration:

```python
import taskbadger
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration

taskbadger.init(
    token="...",
    systems=[ProcrastinateSystemIntegration(
        app=app,
        auto_track_tasks=True,
        includes=[r"myapp\..*"],
        excludes=[r"myapp\.cleanup\..*"],
        record_task_args=True,
    )],
)
```
````

- [ ] **Step 3: Verify markdown renders cleanly**

Run: `uv run python -c "import pathlib, markdown; print('ok' if pathlib.Path('README.md').exists() else 'missing')" 2>/dev/null || echo "Skip if 'markdown' not installed"`

Or just visually inspect that headings and code blocks are well-formed.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(procrastinate): add Procrastinate integration section to README"
```

---

## Final verification

- [ ] **Step 1: Run the full unit test suite**

Run: `uv run pytest -v`

Expected: all existing tests still pass; new procrastinate tests pass.

- [ ] **Step 2: Lint and format**

Run: `uv run ruff check . --fix && uv run ruff format .`

Expected: no errors after autofix.

- [ ] **Step 3: Re-run tests after lint/format**

Run: `uv run pytest -v`

Expected: all pass.

- [ ] **Step 4: Optional — run integration tests if env is available**

Run: `uv run pytest integration_tests/test_procrastinate.py -vs`

Expected: 2 PASS (requires Postgres + TB creds).

- [ ] **Step 5: Commit any lint/format changes**

```bash
git add -u
git commit -m "chore: lint/format procrastinate integration" || echo "Nothing to commit"
```
