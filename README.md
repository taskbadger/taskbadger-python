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
