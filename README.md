# Task Badger Python Client

This is the official Python SDK for [Task Badger](https://taskbadger.net/).

For full documentation go to https://docs.taskbadger.net/python/.

![Integration Tests](https://github.com/taskbadger/taskbadger-python/actions/workflows/integration_tests.yml/badge.svg)

---

## Getting Started

### Install

```bash
pip install --upgrade taskbadger
```

### Client Usage

#### Configuration

```python
import taskbadger

taskbadger.init(
    organization_slug="my-org",
    project_slug="my-project",
    token="***"
)
```

#### Usage with Celery

```python
import taskbadger
from celery import Celery

app = Celery("tasks")

@app.task(bind=True, base=taskbadger.Task)
def my_task(self):
    task = self.taskbadger_task
    for i in range(1000):
        do_something(i)
        if i % 100 == 0:
            task.update(value=i, value_max=1000)
    task.success(value=1000)
```

#### API Example

```python
from taskbadger import Task, Action, EmailIntegration, WebhookIntegration

# create a new task with custom data and an action definition
task = Task.create(
    "task name",
    data={
        "custom": "data"
    },
    actions=[
        Action("*/10%,success,error", integration=EmailIntegration(to="me@example.com")),
        Action("cancelled", integration=WebhookIntegration(id="webhook:demo")),
    ]
)

# update the task status to 'processing' and set the value to 0
task.started()
try:
   for i in range(100):
      do_something(i)
      if i!= 0 and i % 10 == 0:
         # update the progress of the task
         task.update_progress(i)
except Exception as e:
    # record task errors
    task.error(data={
        "error": str(e)
    })
    raise

# record task success
task.success()
```

### CLI USage

#### Configuration

```shell
$ taskbadger configure

Organization slug: my-org
Project slug: project-x
API Key: XYZ.ABC

Config written to ~/.config/taskbadger/config
```

#### Usage Examples

The CLI `run` command executes your command whilst creating and updating a Task Badger task.

```shell
$ taskbadger run "demo task" --action error email to:me@test.com -- path/to/script.sh

Task created: https://taskbadger.net/public/tasks/xyz/
```
