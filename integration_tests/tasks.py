from celery import shared_task

import taskbadger.celery


@shared_task(bind=True, base=taskbadger.celery.Task)
def add(self, x, y):
    assert self.taskbadger_task is not None, "missing task on self"
    self.taskbadger_task.update(value=100, data={"result": x + y})
    return x + y
