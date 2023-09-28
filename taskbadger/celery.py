import functools
import logging

import celery
from celery.signals import before_task_publish, task_failure, task_prerun, task_retry, task_success

from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy, get_task

KWARG_PREFIX = "taskbadger_"
TB_KWARGS_ARG = f"{KWARG_PREFIX}kwargs"
IGNORE_ARGS = {TB_KWARGS_ARG, f"{KWARG_PREFIX}task", f"{KWARG_PREFIX}task_id"}

TERMINAL_STATES = {StatusEnum.SUCCESS, StatusEnum.ERROR, StatusEnum.CANCELLED, StatusEnum.STALE}

log = logging.getLogger("taskbadger")


class Task(celery.Task):
    """A Celery Task that tracks itself with TaskBadger.

    The TaskBadger task will go through the following states:

    - PENDING: The task has been created by calling `.delay()` or `.apply_async()`.
    - PROCESSING: Set when the task starts executing.
    - SUCCESS: The task completed successfully.
    - ERROR: The task failed.

    No tracking is done for tasks that ar executed synchronously either via `.appy()` or
    if Celery is configured to run tasks eagerly.

    Access to the task is provided via the `taskbadger_task` property of the Celery task.
    The task ID may also be accessed via the `taskbadger_task_id` property. These may
    be `None` if the task is not being tracked (e.g. Task Badger is not configured or
    there was an error creating the task).

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
        tb_kwargs = kwargs.pop(TB_KWARGS_ARG, {})
        for name in list(kwargs):
            if name.startswith(KWARG_PREFIX):
                val = kwargs.pop(name)
                tb_kwargs[name.removeprefix(KWARG_PREFIX)] = val
        headers[TB_KWARGS_ARG] = tb_kwargs
        result = super().apply_async(*args, **kwargs)

        tb_task_id = result.info.get("taskbadger_task_id") if result.info else None
        setattr(result, "taskbadger_task_id", tb_task_id)

        _get_task = functools.partial(get_task, tb_task_id) if tb_task_id else lambda: None
        setattr(result, "get_taskbadger_task", _get_task)

        return result

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
            except Exception as e:
                log.exception("Error fetching task '%s'", self.taskbadger_task_id)
                task = None
        return task


@before_task_publish.connect
def task_publish_handler(sender=None, headers=None, **kwargs):
    if not headers.get("taskbadger_track") or not Badger.is_configured():
        return

    ctask = celery.current_app.tasks.get(sender)

    # get kwargs from the task class (set via decorator)
    kwargs = getattr(ctask, TB_KWARGS_ARG, {})
    for attr in dir(ctask):
        if attr.startswith(KWARG_PREFIX) and attr not in IGNORE_ARGS:
            kwargs[attr.removeprefix(KWARG_PREFIX)] = getattr(ctask, attr)

    # get kwargs from the task headers (set via apply_async)
    kwargs.update(headers[TB_KWARGS_ARG])
    kwargs["status"] = StatusEnum.PENDING
    name = kwargs.pop("name", headers["task"])

    task = create_task_safe(name, **kwargs)
    if task:
        meta = {"taskbadger_task_id": task.id}
        headers.update(meta)
        ctask.update_state(task_id=headers["id"], state="PENDING", meta=meta)


@task_prerun.connect
def task_prerun_handler(sender=None, **kwargs):
    _update_task(sender, StatusEnum.PROCESSING)


@task_success.connect
def task_success_handler(sender=None, **kwargs):
    _update_task(sender, StatusEnum.SUCCESS)
    exit_session(sender)


@task_failure.connect
def task_failure_handler(sender=None, einfo=None, **kwargs):
    _update_task(sender, StatusEnum.ERROR, einfo)
    exit_session(sender)


@task_retry.connect
def task_retry_handler(sender=None, einfo=None, **kwargs):
    _update_task(sender, StatusEnum.ERROR, einfo)
    exit_session(sender)


def _update_task(signal_sender, status, einfo=None):
    log.debug("celery_task_update %s %s", signal_sender, status)
    if not hasattr(signal_sender, "taskbadger_task"):
        return

    task = signal_sender.taskbadger_task
    if task is None:
        return

    if task.status in TERMINAL_STATES:
        # ignore tasks that have already been set to a terminal state (probably in the task body)
        return

    enter_session()

    data = None
    if einfo:
        data = DefaultMergeStrategy().merge(task.data, {"exception": str(einfo)})
    update_task_safe(task.id, status=status, data=data)


def enter_session():
    if not Badger.is_configured():
        return
    session = Badger.current.session()
    if not session.client:
        session.__enter__()


def exit_session(signal_sender):
    if not hasattr(signal_sender, "taskbadger_task") or not Badger.is_configured():
        return
    session = Badger.current.session()
    if session.client:
        session.__exit__()
