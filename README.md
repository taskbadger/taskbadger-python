# Task Badger Python Client

This is the official Python SDK for [Task Badger](https://taskbadger.net/).

For full documentation go to https://docs.taskbadger.net/python/.

![Integration Tests](https://github.com/taskbadger/taskbadger-python/actions/workflows/integration_tests.yml/badge.svg)

---

## Getting Started

### Install

```bash
pip install taskbadger
```

To use the `taskbadger` command-line tool, install the `cli` extra:

```bash
pip install 'taskbadger[cli]'
```

### Client Usage

```python
import taskbadger
from taskbadger.systems import CelerySystemIntegration

taskbadger.init(
    token="***",
    systems=[CelerySystemIntegration()],
    tags={"environment": "production"}
)
```

### CLI Usage

```shell
$ export TASKBADGER_API_KEY=***
$ taskbadger run "nightly-backup" -- ./backup.sh
```

### Procrastinate Integration

The SDK includes optional support for the [Procrastinate](https://procrastinate.readthedocs.io/) task queue.

Install with the extra:

```bash
pip install 'taskbadger[procrastinate]'
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
            tb.update(value=i)
```

To auto-track every task on an App, register the system integration:

```python
import taskbadger
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration

taskbadger.init(
    token="***",
    systems=[ProcrastinateSystemIntegration(
        app=app,
        auto_track_tasks=True,
        includes=[r"myapp\..*"],
        excludes=[r"myapp\.cleanup\..*"],
        record_task_args=True,
    )],
)
```

#### Known limitations

- **`task.configure(...).defer(...)` is not tracked.** Procrastinate's `configure()` returns a separate `JobDeferrer` whose methods bypass our wrapper. Use `task.defer(...)` directly for tracked deferrals. Tasks deferred via `configure().defer()` will run normally but will not appear in TaskBadger.
- **`task.batch_defer*` is not tracked.** Same reason as `configure().defer()`.
- **Tasks added via `app.add_tasks_from(blueprint)` after `ProcrastinateSystemIntegration` is constructed are not auto-instrumented.** Construct the integration after all blueprints are registered, or apply `@track` to those tasks explicitly.
