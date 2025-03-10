import datetime
from uuid import uuid4

from taskbadger.internal.models import Task as TaskInternal


def task_for_test(**kwargs):
    task_id = kwargs.pop("id", uuid4().hex)
    data = kwargs.pop("data", None)
    if data:
        kwargs["data"] = data
    kwargs["url"] = None
    kwargs["public_url"] = None
    kwargs["value_percent"] = None
    kwargs["created"] = datetime.datetime.now(datetime.timezone.utc)
    kwargs["updated"] = datetime.datetime.now(datetime.timezone.utc)
    return TaskInternal(
        task_id,
        "org",
        "project",
        "task_name",
        **kwargs,
    )
