import logging
from typing import Any

import celery
from celery.signals import before_task_publish, task_failure, task_retry, task_success

from .internal.models import StatusEnum
from .mug import Badger
from .sdk import create_task, get_task, update_task

log = logging.getLogger("taskbadger")


class Task(celery.Task):
    """A Celery Task that tracks itself with TaskBadger."""

    def apply_async(self, *args, **kwargs):
        headers = kwargs.setdefault("headers", {})
        headers["taskbadger_track"] = True
        return super().apply_async(*args, **kwargs)

    @property
    def taskbadger_task_id(self):
        return self.request and self.request.headers and self.request.headers.get("taskbadger_task_id")

    @property
    def taskbadger_task(self):
        if not self.taskbadger_task_id:
            return None

        task = self.request.get("taskbadger_task")
        if not task:
            try:
                task = get_task(self.taskbadger_task_id)
                self.request.update({"taskbadger_task": task})
            except Exception:
                log.exception("Error fetching task '%s'", self.taskbadger_task_id)
                task = None
        return task


@before_task_publish.connect
def task_publish_handler(sender=None, headers=None, **kwargs):
    if not headers.get("taskbadger_track") or not Badger.is_configured():
        return

    name = headers["task"]
    try:
        task = create_task(
            name,
            status=StatusEnum.PRE_PROCESSING,
        )
    except Exception:
        log.exception("Error creating task '%s'", name)
    else:
        headers.update(
            {
                "taskbadger_task_id": task.id,
            }
        )


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    log.debug("celery_task_success %s", sender)
    headers = sender.request.get("headers") or {}

    task_id = headers.get("taskbadger_task_id")
    if not task_id:
        return

    try:
        update_task(task_id, status=StatusEnum.SUCCESS)
    except Exception:
        log.exception("Error updating task '%s'", task_id)


@task_failure.connect
def task_failure_handler(sender=None, result=None, **kwargs):
    pass


@task_retry.connect
def task_retry_handler(sender=None, result=None, **kwargs):
    pass
