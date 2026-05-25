# Procrastinate Integration — Design

## Goal

Add first-class support for the [Procrastinate](https://procrastinate.readthedocs.io/) task queue, paralleling the existing Celery integration. Users should be able to:

1. Opt individual tasks into TaskBadger tracking via a `@track` decorator.
2. Auto-track all tasks on a Procrastinate `App` via a `ProcrastinateSystemIntegration`, with regex-based includes/excludes.
3. See the full lifecycle of a job — PENDING at defer time, PROCESSING at worker start, SUCCESS/ERROR at worker end.
4. Access the current TaskBadger task from inside the running job to update progress/data.

## Non-goals

- No support for Procrastinate's job-cancellation/abort flow as a distinct TB state (cancelled/aborted jobs surface as ERROR, same as Celery retries).
- No per-`defer()` overrides (no `taskbadger_kwargs={...}` on the defer call). All TB-side opts are set at task-decoration time.
- No tracking of Procrastinate retries as a separate TB state — matches Celery integration's `task_retry_handler`.

## Why this is shaped differently from Celery

Procrastinate has no signals or middleware system. The only extension point is wrapping the task function and the `defer` methods. We compensate by:

- Smuggling the TB task id through Procrastinate's `task_kwargs` under a reserved key (`__taskbadger_task_id__`), stripping it before calling the user function.
- Exposing the current TB task via a `ContextVar` set by our wrapper (no `self` to attach to — Procrastinate tasks are plain functions).
- Monkey-patching `app.task` so newly-registered tasks are wrapped at registration when auto-track is on.

## Architecture

```
taskbadger/
  procrastinate.py            # public API: @track decorator, current_task(), wrap helpers
  systems/
    procrastinate.py          # ProcrastinateSystemIntegration
integration_tests/
  test_procrastinate.py       # real Postgres + Procrastinate
tests/
  test_procrastinate.py
  test_procrastinate_system_integration.py
```

All `procrastinate` imports are inside `taskbadger/procrastinate.py` and `taskbadger/systems/procrastinate.py`. The package's top-level `__init__.py` is untouched, so users without procrastinate installed see no import failures.

`pyproject.toml`:

- `[project.optional-dependencies]` gets `procrastinate = ["procrastinate>=3.0"]`.
- `[dependency-groups].dev` adds `procrastinate`.

## Lifecycle and id-threading

### At defer time (wrapping `task.defer` and `task.defer_async`)

1. Look up TB-side opts attached to the task at decoration time (`name`, `value_max`, `tags`, `data`, `record_task_args`).
2. Decide whether to track:
   - `manual` — task was decorated with `@track`, OR
   - `auto` — the configured `ProcrastinateSystemIntegration.track_task(name)` returns True.
3. If `Badger.is_configured()` AND (`manual` or `auto`):
   - If `record_task_args` is on (either per-task or via the system's `record_task_args`), JSON-serialize the defer kwargs and merge under `data["procrastinate_task_kwargs"]`.
   - Call `create_task_safe(name, status=PENDING, **opts)`.
   - If a task was created, inject its id into the defer kwargs as `__taskbadger_task_id__=<id>`.
4. Call the original defer with the (possibly modified) kwargs and return its result.

If `Badger.is_configured()` is False, or `create_task_safe` returns None, no key is injected and the defer runs untouched.

### At worker time (wrapping the task function)

1. Pop `__taskbadger_task_id__` from kwargs. If absent → run user function with no TB activity.
2. Set the `_current_tb_task_id` `ContextVar`.
3. Call `update_task_safe(id, status=PROCESSING)`. If this fails, log and continue (consistent with the safe_sdk pattern).
4. Invoke the user function. Use `inspect.iscoroutinefunction` on the original function to dispatch sync vs async correctly.
5. On exception:
   - Fetch the current task (cached). If it's already in a terminal state (user set it in the body), skip the update.
   - Otherwise call `update_task_safe(id, status=ERROR, data={"exception": str(exc)})` merged with existing data via `DefaultMergeStrategy`.
   - Re-raise so Procrastinate's retry logic still runs.
6. On success: same terminal-state check, then `update_task_safe(id, status=SUCCESS)`.
7. Reset the `ContextVar`.

### `pass_context=True` compatibility

Procrastinate's `@app.task(pass_context=True)` injects a `JobContext` as the first positional arg. Our wrapper detects this from the procrastinate task object's attributes (`task.pass_context`) and forwards context unchanged. The `__taskbadger_task_id__` kwarg is popped from `kwargs`, not from the context.

## Public API

### `taskbadger.procrastinate.track`

Per-task opt-in. Applied *outside* `@app.task`:

```python
import procrastinate
import taskbadger
from taskbadger.procrastinate import track

app = procrastinate.App(connector=...)

@track  # bare form, defaults
@app.task(queue="sums")
async def add(a, b):
    return a + b

@track(name="custom-name", value_max=100, tags={"env": "prod"}, record_task_args=True)
@app.task
async def big_job(payload): ...
```

`track` accepts these kwargs (all optional):
- `name` — overrides the procrastinate task name when creating the TB task. Defaults to the procrastinate task's `name` attribute.
- `value_max` — sets the TB task's `value_max`.
- `tags` — dict passed through to TB.
- `data` — dict merged into the TB task's `data`. If `record_task_args` is on, the recorded args are merged on top under `procrastinate_task_kwargs` (user-supplied keys are preserved unless they collide with that reserved key).
- `record_task_args` — bool, defaults to None (= "inherit from system integration if configured, else False").

`@track` supports both bare (`@track`) and parameterized (`@track(name="...")`) forms using the standard `original_func=None` pattern.

`@track` sets `task._taskbadger_manual = True` and calls `_instrument_task(task, system=None)`. Idempotent if already instrumented.

### `taskbadger.procrastinate.current_task()`

Returns the TB `Task` for the currently-running job (or `None` if no job, no tracking, or fetch failed). Uses the same LRU cache pattern as `taskbadger.celery.safe_get_task`.

```python
from taskbadger.procrastinate import current_task

@track
@app.task
async def report_progress(items):
    tb = current_task()
    for i, item in enumerate(items):
        await process(item)
        if i % 10 == 0:
            tb.update(value=i, value_max=len(items))
```

### `taskbadger.systems.procrastinate.ProcrastinateSystemIntegration`

```python
import taskbadger
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration

taskbadger.init(
    organization_slug="...",
    project_slug="...",
    token="...",
    systems=[ProcrastinateSystemIntegration(
        app=my_procrastinate_app,
        auto_track_tasks=True,
        includes=[r"myapp\..*"],
        excludes=[r"myapp\.cleanup\..*"],
        record_task_args=False,
    )],
)
```

Constructor:
- `app` — required, the `procrastinate.App` instance to instrument.
- `auto_track_tasks` — default True.
- `includes` / `excludes` — lists of regex strings, same semantics as `CelerySystemIntegration` (`re.fullmatch`, excludes take precedence).
- `record_task_args` — default False.

On `__init__`:
1. Iterate `app.tasks.values()` and call `_instrument_task(task, system=self)` on each.
2. Replace `app.task` with a wrapper that instruments newly-registered tasks. Store the original under `app._taskbadger_original_task` to make the patch idempotent.

`track_task(name)` — same regex precedence logic as `CelerySystemIntegration.track_task`.

### `taskbadger.systems.procrastinate._instrument_task(task, system)` (private)

- Checks `task._taskbadger_instrumented`; if set, returns.
- Replaces `task.func` with the wrapped function (built around the original `task.func`).
- Wraps `task.defer` and `task.defer_async`.
- Marks `task._taskbadger_instrumented = True` and stores the system reference on `task._taskbadger_system`.

When both `@track` and auto-track apply, the first one wins (idempotent). `@track`'s manual flag is preserved on the task object even after the system integration runs.

## Error handling

Same envelope as the Celery integration:
- All TB SDK calls go through `safe_*` wrappers, which log and swallow exceptions.
- Worker-side wrapper never suppresses the user's exception — it re-raises after updating TB.
- Defer-side wrapper never blocks a defer on TB failure — if `create_task_safe` returns None, defer still proceeds.

## Testing

### Unit tests (`tests/test_procrastinate.py`)

Use `procrastinate.testing.InMemoryConnector` — no real Postgres needed.

- `test_track_decorator_sync` / `test_track_decorator_async` — defer + run, asserts `create_task_safe` called once, `update_task_safe` called for PROCESSING and SUCCESS.
- `test_track_decorator_with_opts` — name/value_max/tags/data flow through.
- `test_track_decorator_with_record_task_args` — defer kwargs land in `data["procrastinate_task_kwargs"]`.
- `test_track_error` — task raises, ERROR update with exception in data, exception re-raised.
- `test_track_passes_context` — `pass_context=True` task gets context forwarded.
- `test_current_task_accessor` — `current_task()` returns the right task inside the body.
- `test_terminal_state_in_body` — user sets SUCCESS inside, wrapper does not overwrite.
- `test_badger_not_configured_at_defer` — no TB calls, no kwarg injected, task runs clean.
- `test_badger_not_configured_at_worker` — id present but Badger unconfigured at worker; kwarg still popped, task runs clean.
- `test_double_wrap_idempotent` — `@track` then system integration on same task.

### System-integration tests (`tests/test_procrastinate_system_integration.py`)

- `test_auto_track_all` — every task instrumented.
- `test_includes_excludes` — regex precedence rules.
- `test_auto_track_off_skips_creation` — `auto_track_tasks=False` plus undecorated task → no TB calls.
- `test_wraps_existing_tasks` — tasks registered before system init are instrumented.
- `test_wraps_new_tasks` — tasks registered after system init are instrumented (monkey-patch verified).

### Integration test (`integration_tests/test_procrastinate.py`)

Uses `procrastinate.PsycopgConnector` against a real Postgres. Mirrors `integration_tests/test_celery.py`:
- Requires `TASKBADGER_ORG`, `TASKBADGER_PROJECT`, `TASKBADGER_API_KEY`, plus a Postgres DSN env var.
- One async task using `@track` that updates progress inside the body.
- One auto-tracked task via `ProcrastinateSystemIntegration`.
- Excluded from the default pytest run via the existing `norecursedirs`.

## Open items

- README docs: a short Procrastinate section paralleling the existing Celery section. To be added as part of the implementation (not separately specified here).

## Edge cases worth keeping in mind during implementation

- Procrastinate jobs are JSON-serialized; the TB task id is a string so injection into `task_kwargs` is safe.
- Sync tasks run in their own thread (per Procrastinate). The `ContextVar` for `current_task` must be set inside the thread that runs the task. Procrastinate copies context appropriately for async; for sync tasks we'll set/reset within the same call so the per-thread copy is correct.
- If a user calls `task.defer(...)` from inside another tracked task, the inner defer should still work — `create_task_safe` is independent of the running task's session, and the contextvar is per-call.
