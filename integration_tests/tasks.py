import time

from celery import shared_task

import taskbadger.celery

HEARTBEAT_INTERVAL = 1
# long enough to sample the task's `updated` time while it is still running
SLOW_ADD_DURATION = 6


@shared_task(bind=True, base=taskbadger.celery.Task)
def add(self, x, y):
    assert self.taskbadger_task is not None, "missing task on self"
    self.taskbadger_task.update(value=100, data={"result": x + y})
    return x + y


@shared_task(bind=True)
def add_auto_track(self, x, y):
    assert self.request.taskbadger_task_id is not None, "missing task ID on self.request"
    return x + y


@shared_task(bind=True, base=taskbadger.celery.Task, taskbadger_heartbeat_interval=HEARTBEAT_INTERVAL)
def slow_add(self, x, y):
    """Runs long enough to go stale without a heartbeat, and never updates itself."""
    time.sleep(SLOW_ADD_DURATION)
    return x + y
