import logging

import celery
from celery.signals import before_task_publish, task_failure, task_prerun, task_retry, task_success

from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy, get_task

log = logging.getLogger("taskbadger")


class Task(celery.Task):
    """A Celery Task that tracks itself with TaskBadger.

    Examples:
        .. code-block:: python

            @app.task(base=taskbadger.Task)
            def refresh_feed(url):
                store_feed(feedparser.parse(url))

        with access to the task in the function body:

        .. code-block:: python

            @app.task(bind=True, base=taskbadger.Task)
            def scrape_urls(self, urls):
                task = self.taskbadger_task
                total_urls = len(urls)
                for i, url in enumerate(urls):
                    scrape_url(url)
                    if i % 10 == 0:
                        task.update(value=i, value_max=total_urls)
                task.success(value=total_urls)
    """

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
            log.debug("Fetching task '%s'", self.taskbadger_task_id)
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
    task_id = create_task_safe(
        name,
        status=StatusEnum.PRE_PROCESSING,
    )
    if task_id:
        headers.update({"taskbadger_task_id": task_id})


@task_prerun.connect
def task_prerun_handler(sender=None, **kwargs):
    _update_task(sender, StatusEnum.PROCESSING)


@task_success.connect
def task_success_handler(sender=None, **kwargs):
    _update_task(sender, StatusEnum.SUCCESS)


@task_failure.connect
def task_failure_handler(sender=None, einfo=None, **kwargs):
    _update_task(sender, StatusEnum.ERROR, einfo)


@task_retry.connect
def task_retry_handler(sender=None, einfo=None, **kwargs):
    _update_task(sender, StatusEnum.ERROR, einfo)


def _update_task(signal_sender, status, einfo=None):
    log.debug("celery_task_success %s", signal_sender)

    task = signal_sender.taskbadger_task
    if not task:
        return

    data = None
    if einfo:
        data = DefaultMergeStrategy().merge(task.data, {"exception": str(einfo)})
    update_task_safe(task.id, status=status, data=data)
