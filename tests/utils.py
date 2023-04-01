from datetime import datetime

from taskbadger.internal.models import TaskData, Task as TaskInternal


def task_for_test(**kwargs):
    data = kwargs.pop("data", None)
    if data:
        kwargs["data"] = TaskData.from_dict(data)
    kwargs["url"] = None
    kwargs["public_url"] = None
    kwargs["value_percent"] = None
    return TaskInternal(
        "test_id", "org", "project", "task_name", datetime.utcnow(), datetime.utcnow(), **kwargs
    )
