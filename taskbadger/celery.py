import collections
import functools
import json
import logging

import celery
from celery.signals import (
    before_task_publish,
    task_failure,
    task_prerun,
    task_retry,
    task_success,
)
from kombu import serialization

from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy, get_task

KWARG_PREFIX = "taskbadger_"
TB_KWARGS_ARG = f"{KWARG_PREFIX}kwargs"
IGNORE_ARGS = {TB_KWARGS_ARG, f"{KWARG_PREFIX}task", f"{KWARG_PREFIX}task_id", f"{KWARG_PREFIX}record_task_args"}
TB_TASK_ID = f"{KWARG_PREFIX}task_id"

TERMINAL_STATES = {
    StatusEnum.SUCCESS,
    StatusEnum.ERROR,
    StatusEnum.CANCELLED,
    StatusEnum.STALE,
}

log = logging.getLogger("taskbadger")


class Cache:
    def __init__(self, maxsize=128):
        self.cache = collections.OrderedDict()
        self.maxsize = maxsize

    def set(self, key, value):
        self.cache[key] = value

    def unset(self, key):
        self.cache.pop(key, None)

    def get(self, key):
        return self.cache.get(key)

    def prune(self):
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)


def cached(cache_none=True, maxsize=128):
    cache = Cache(maxsize=maxsize)

    def _wrapper(func):
        @functools.wraps(func)
        def _inner(*args, **kwargs):
            key = args + tuple(sorted(kwargs.items()))
            if key in cache.cache:
                return cache.get(key)

            result = func(*args, **kwargs)
            if result is not None or cache_none:
                cache.set(key, result)
            return result

        _inner.cache = cache
        return _inner

    return _wrapper


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
        tb_kwargs = self._get_tb_kwargs(kwargs)
        if kwargs.get("kwargs"):
            # extract taskbadger options from task kwargs when supplied as keyword argument
            tb_kwargs.update(self._get_tb_kwargs(kwargs["kwargs"]))
        elif len(args) > 1 and isinstance(args[1], dict):
            # extract taskbadger options from task kwargs when supplied as positional argument
            tb_kwargs.update(self._get_tb_kwargs(args[1]))

        if Badger.is_configured():
            headers["taskbadger_track"] = True
            headers[TB_KWARGS_ARG] = tb_kwargs
            if "record_task_args" in tb_kwargs:
                headers["taskbadger_record_task_args"] = tb_kwargs.pop("record_task_args")

        result = super().apply_async(*args, **kwargs)

        tb_task_id = result.info.get(TB_TASK_ID) if result.info else None
        setattr(result, TB_TASK_ID, tb_task_id)

        _get_task = functools.partial(get_task, tb_task_id) if tb_task_id else lambda: None
        setattr(result, "get_taskbadger_task", _get_task)

        return result

    def _get_tb_kwargs(self, kwargs):
        tb_kwargs = kwargs.pop(TB_KWARGS_ARG, {})
        for name in list(kwargs):
            if name.startswith(KWARG_PREFIX):
                val = kwargs.pop(name)
                tb_kwargs[name.removeprefix(KWARG_PREFIX)] = val
        return tb_kwargs

    @property
    def taskbadger_task_id(self):
        return _get_taskbadger_task_id(self.request)

    @property
    def taskbadger_task(self):
        if not self.taskbadger_task_id:
            return None

        task = self.request.get("taskbadger_task")
        if not task:
            log.debug("Fetching task '%s'", self.taskbadger_task_id)
            task = safe_get_task(self.taskbadger_task_id)
            if task:
                self.request.update({"taskbadger_task": task})
        return task


@before_task_publish.connect
def task_publish_handler(sender=None, headers=None, body=None, **kwargs):
    headers = headers if "task" in headers else body
    header_kwargs = headers.pop(TB_KWARGS_ARG, {})  # always remove TB headers
    if sender.startswith("celery.") or not Badger.is_configured():
        return

    celery_system = Badger.current.settings.get_system_by_id("celery")
    auto_track = celery_system and celery_system.track_task(sender)
    manual_track = headers.get("taskbadger_track")
    if not manual_track and not auto_track:
        return

    ctask = celery.current_app.tasks.get(sender)

    # get kwargs from the task class (set via decorator)
    kwargs = getattr(ctask, TB_KWARGS_ARG, {})
    for attr in dir(ctask):
        if attr.startswith(KWARG_PREFIX) and attr not in IGNORE_ARGS:
            kwargs[attr.removeprefix(KWARG_PREFIX)] = getattr(ctask, attr)

    # get kwargs from the task headers (set via apply_async)
    kwargs.update(header_kwargs)
    kwargs["status"] = StatusEnum.PENDING
    name = kwargs.pop("name", headers["task"])

    global_record_task_args = celery_system and celery_system.record_task_args
    if headers.get("taskbadger_record_task_args", global_record_task_args):
        data = {
            "celery_task_args": body[0],
            "celery_task_kwargs": body[1],
        }
        try:
            _, _, value = serialization.dumps(data, serializer="json")
            data = json.loads(value)
        except Exception:
            log.error("Error serializing task arguments for task '%s'", name)
        else:
            kwargs.setdefault("data", {}).update(data)

    task = create_task_safe(name, **kwargs)
    if task:
        meta = {TB_TASK_ID: task.id}
        headers.update(meta)
        ctask.update_state(task_id=headers["id"], state="PENDING", meta=meta)


def _maybe_create_task(signal_sender):
    """Create a TaskBadger task if one doesn't exist yet.

    This handles cases where before_task_publish didn't fire or was skipped:
    - Eager mode (before_task_publish doesn't fire)
    - Canvas primitives like map/starmap/chunks (fire for celery.* tasks)
    """
    # Check if task was already created FIRST (before accessing Badger)
    # This avoids initializing thread-local Badger state for tasks like celery.ping
    task_id = _get_taskbadger_task_id(signal_sender.request)
    if task_id:
        return

    task_name = signal_sender.name

    # Skip built-in celery tasks that we don't track (like celery.ping)
    # Only handle celery.map and celery.starmap specially
    if task_name.startswith("celery.") and task_name not in ("celery.map", "celery.starmap"):
        return

    # For non-canvas tasks, only create if there was an explicit intent to track
    # (indicated by taskbadger_track header). This prevents creating tasks when
    # Badger wasn't configured at publish time but has stale config in worker.
    headers = signal_sender.request.headers or {}
    is_canvas_task = task_name in ("celery.map", "celery.starmap")
    if not is_canvas_task and not headers.get("taskbadger_track"):
        return

    # NOW it's safe to check Badger configuration
    if not Badger.is_configured():
        return

    celery_system = Badger.current.settings.get_system_by_id("celery")
    data = None
    inner_task = None

    # Handle celery.map and celery.starmap - extract the inner task name
    if task_name in ("celery.map", "celery.starmap"):
        canvas_type = task_name.split(".")[-1]  # "map" or "starmap"
        inner_task_info = signal_sender.request.kwargs.get("task")
        if inner_task_info:
            # inner_task_info can be a dict (serialized signature) or a Signature object
            if isinstance(inner_task_info, dict):
                task_name = inner_task_info.get("task", task_name)
            elif hasattr(inner_task_info, "name"):
                task_name = inner_task_info.name
            # Get the actual task class to check if it uses Task base
            inner_task = celery.current_app.tasks.get(task_name)
        items = signal_sender.request.kwargs.get("it", [])
        # Convert to list if needed for counting and potential recording
        items_list = list(items) if not isinstance(items, (list, tuple)) else items
        item_count = len(items_list)
        # Append canvas type and item count to task name
        task_name = f"{task_name} ({canvas_type} {item_count})"
        data = {"canvas_type": signal_sender.name, "item_count": item_count}

        # Include task items if record_task_args is enabled
        if celery_system and celery_system.record_task_args:
            try:
                _, _, value = serialization.dumps({"items": items_list}, serializer="json")
                items_data = json.loads(value)
                data["celery_task_items"] = items_data["items"]
            except Exception:
                log.warning("Error serializing canvas items for task '%s'", task_name)

    # Check if we should track this task
    auto_track = celery_system and celery_system.track_task(task_name)
    # Check if the task (or inner task for map/starmap) uses our Task base class
    task_to_check = inner_task if inner_task else signal_sender
    manual_track = isinstance(task_to_check, Task)
    if not manual_track and not auto_track:
        return

    enter_session()

    task = create_task_safe(task_name, status=StatusEnum.PENDING, data=data)
    if task:
        # Store the task ID in the request so _update_task can find it
        signal_sender.request.update({TB_TASK_ID: task.id})
        safe_get_task.cache.set((task.id,), task)


@task_prerun.connect
def task_prerun_handler(sender=None, **kwargs):
    _maybe_create_task(sender)
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
    task_id = _get_taskbadger_task_id(signal_sender.request)
    if not task_id:
        return

    log.debug("celery_task_update %s %s", signal_sender, status)
    if hasattr(signal_sender, "taskbadger_task"):
        task = signal_sender.taskbadger_task
    else:
        task = safe_get_task(task_id)

    if task is None:
        return

    if task.status in TERMINAL_STATES:
        # ignore tasks that have already been set to a terminal state (probably in the task body)
        return

    enter_session()

    data = None
    if einfo:
        data = DefaultMergeStrategy().merge(task.data, {"exception": str(einfo)})
    task = update_task_safe(task.id, status=status, data=data)
    if task:
        safe_get_task.cache.set((task_id,), task)


def enter_session():
    if not Badger.is_configured():
        return
    session = Badger.current.session()
    if not session.client:
        session.__enter__()


def exit_session(signal_sender):
    headers = signal_sender.request.headers
    if not headers:
        return

    task_id = headers.get(TB_TASK_ID)
    if not task_id or not Badger.is_configured():
        return

    safe_get_task.cache.unset((task_id,))
    safe_get_task.cache.prune()

    session = Badger.current.session()
    if session.client:
        session.__exit__()


@cached(cache_none=False)
def safe_get_task(task_id: str):
    try:
        return get_task(task_id)
    except Exception as e:
        log.warning("Error fetching task '%s': %s", task_id, e)


def _get_taskbadger_task_id(request):
    if not request:
        return

    task_id = request.get(TB_TASK_ID)
    if task_id:
        return task_id

    if request.headers:
        return request.headers.get(TB_TASK_ID)
