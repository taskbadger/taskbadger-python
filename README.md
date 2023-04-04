# Task Badger Python Client

This is the official Python SDK for [Task Badger](https://taskbadger.net/).

For full documentation go to https://docs.taskbadger.net/python/.

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

#### API Example

```python
from taskbadger import Task, Action, EmailIntegration

# create a new task with custom data and an action definition
task = Task.create(
    "task name",
    data={
        "custom": "data"
    },
    actions=[
        Action(
            "*/10%,success,error",
            integration=EmailIntegration(to="me@example.com")
        )
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
Config written to ~/.config/taskbadger/confi
```

#### Usage Examples

The CLI `run` command executes your command whilst creating and updating a Task Badger task.

```shell
$ taskbadger run "demo task" --action "error email to:me@test.com" -- path/to/script.sh
Task created: https://taskbadger.net/public/tasks/xyz/
```

