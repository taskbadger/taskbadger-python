from datetime import datetime
from uuid import uuid4

from taskbadger.internal.models import Task as TaskInternal
from taskbadger.internal.models import TaskData


def task_for_test(**kwargs):
    data = kwargs.pop("data", None)
    if data:
        kwargs["data"] = TaskData.from_dict(data)
    kwargs["url"] = None
    kwargs["public_url"] = None
    kwargs["value_percent"] = None
    return TaskInternal(uuid4().hex, "org", "project", "task_name", datetime.utcnow(), datetime.utcnow(), **kwargs)
