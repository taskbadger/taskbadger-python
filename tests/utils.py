from datetime import datetime
from uuid import uuid4

from taskbadger.internal.models import Task as TaskInternal
from taskbadger.internal.models import TaskDataType0


def task_for_test(**kwargs):
    task_id = kwargs.pop("id", uuid4().hex)
    data = kwargs.pop("data", None)
    if data:
        kwargs["data"] = TaskDataType0.from_dict(data)
    kwargs["url"] = None
    kwargs["public_url"] = None
    kwargs["value_percent"] = None
    kwargs["created"] = datetime.utcnow()
    kwargs["updated"] = datetime.utcnow()
    return TaskInternal(
        task_id,
        "org",
        "project",
        "task_name",
        **kwargs,
    )
