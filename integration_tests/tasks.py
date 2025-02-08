from celery import shared_task

import taskbadger.celery


@shared_task(bind=True, base=taskbadger.celery.Task)
def add(self, x, y):
    assert self.taskbadger_task is not None, "missing task on self"
    self.taskbadger_task.update(value=100, data={"result": x + y})
    return x + y


@shared_task(bind=True)
def add_auto_track(self, x, y):
    assert (
        self.request.taskbadger_task_id is not None
    ), "missing task ID on self.request"
    return x + y
