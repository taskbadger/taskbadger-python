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


@shared_task(bind=True, base=taskbadger.celery.Task)
def spawns_grandchild(self, x, y):
    """Deferred by `spawns_child`, and defers a task of its own in turn.

    Since this is already a child, the task it defers has to be flattened onto
    the root rather than nested under this one — the API only allows one level.
    """
    grandchild = add.delay(x, y)
    return {"own_tb_id": self.taskbadger_task_id, "grandchild_tb_id": grandchild.taskbadger_task_id}


@shared_task(bind=True, base=taskbadger.celery.Task)
def spawns_child(self, x, y):
    """Defers a task from inside its own run, so that task nests under this one."""
    return spawns_grandchild.delay(x, y).id


@shared_task(bind=True, base=taskbadger.celery.Task)
def chain_head(self):
    return self.taskbadger_task_id


@shared_task(bind=True, base=taskbadger.celery.Task)
def chain_tail(self, head_tb_id):
    return {"head_tb_id": head_tb_id, "own_tb_id": self.taskbadger_task_id}


@shared_task(bind=True, base=taskbadger.celery.Task, taskbadger_heartbeat_interval=HEARTBEAT_INTERVAL)
def slow_add(self, x, y):
    """Runs long enough to go stale without a heartbeat, and never updates itself."""
    time.sleep(SLOW_ADD_DURATION)
    return x + y
