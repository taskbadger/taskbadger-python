import functools
import json
import logging

import celery
from celery.signals import (
    before_task_publish,
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    task_success,
)
from kombu import serialization

from . import sdk
from ._current_task import enter_task, exit_task, parent_id
from ._error_context import capture_error_data, reset_error_context, start_error_context
from ._heartbeat import heartbeat
from ._integrations import TERMINAL_STATES, parent_of, resolve_heartbeat_options, safe_get_task, task_cache
from .internal.models import StatusEnum
from .mug import Badger
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy

KWARG_PREFIX = "taskbadger_"
TB_KWARGS_ARG = f"{KWARG_PREFIX}kwargs"
IGNORE_ARGS = {TB_KWARGS_ARG, f"{KWARG_PREFIX}task", f"{KWARG_PREFIX}task_id", f"{KWARG_PREFIX}record_task_args"}
TB_TASK_ID = f"{KWARG_PREFIX}task_id"
TB_HEARTBEAT_INTERVAL = f"{KWARG_PREFIX}heartbeat_interval"
TB_STALE_TIMEOUT = f"{KWARG_PREFIX}stale_timeout"
# Marks a request whose signal handlers opened the Task Badger session, so that
# only they close it again.
TB_OWNS_SESSION = f"{KWARG_PREFIX}owns_session"
# Token returned by start_error_context(), stashed on the request so
# task_postrun_handler can restore the previous context (see comment there).
TB_ERROR_CTX_TOKEN = f"{KWARG_PREFIX}error_ctx_token"
# Token returned by enter_task(), stashed on the request so task_postrun_handler
# can clear the task again once it has finished running.
TB_CURRENT_TASK_TOKEN = f"{KWARG_PREFIX}current_task_token"

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

    Task Badger options may be set as `taskbadger_`-prefixed arguments on the task or on
    `apply_async`. `taskbadger_heartbeat_interval` is treated specially: rather than being
    set on the task it makes the worker ping the task every N seconds while it runs, which
    keeps tasks with a `stale_timeout` from going stale. Unless `taskbadger_stale_timeout`
    is also given it is set to twice the interval.

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

        info = result.info
        tb_task_id = info.get(TB_TASK_ID) if isinstance(info, dict) else None
        setattr(result, TB_TASK_ID, tb_task_id)

        _get_task = functools.partial(sdk.get_task, tb_task_id) if tb_task_id else lambda: None
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


def _signature_names(signature):
    """The task names ``signature`` will publish, expanding groups.

    Signatures reach us either as ``Signature`` objects or as the dicts they
    serialize to, depending on where in Celery they came from.
    """
    if isinstance(signature, dict):
        name = signature.get("task")
        nested = (signature.get("kwargs") or {}).get("tasks")
    else:
        name = getattr(signature, "task", None)
        nested = getattr(signature, "tasks", None)
    if nested:
        for inner in nested:
            yield from _signature_names(inner)
    elif name:
        yield name


def _is_workflow_successor(task_name):
    """Whether the task being published is the running task's next chain link or
    one of its callbacks, rather than something its body chose to enqueue.

    Celery dispatches both from inside ``trace_task`` after the task body
    returns but before ``task_postrun``, so the running task still looks
    current. They're the task's successors rather than its subtasks, so they
    shouldn't be nested under it.
    """
    request = getattr(celery.current_task, "request", None)
    if request is None:
        return False
    successors = list(request.chain or []) + list(request.callbacks or [])
    return any(name == task_name for sig in successors for name in _signature_names(sig))


@before_task_publish.connect
def task_publish_handler(sender=None, headers=None, body=None, **kwargs):
    routing_key = kwargs.get("routing_key")
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
    # copy: the raw attr is shared across invocations, and we mutate per-publish
    # values (external_id, status, name) into it below
    kwargs = dict(getattr(ctask, TB_KWARGS_ARG, {}))
    for attr in dir(ctask):
        if attr.startswith(KWARG_PREFIX) and attr not in IGNORE_ARGS:
            kwargs[attr.removeprefix(KWARG_PREFIX)] = getattr(ctask, attr)

    # get kwargs from the task headers (set via apply_async)
    kwargs.update(header_kwargs)
    kwargs["status"] = StatusEnum.PENDING
    if routing_key and "queue" not in kwargs:
        kwargs["queue"] = routing_key
    kwargs.setdefault("external_id", headers["id"])
    # `before_task_publish` fires in the process doing the publishing, so if that
    # is itself a tracked task this nests the new task under it.
    enclosing_task = parent_id()
    if enclosing_task and not _is_workflow_successor(sender):
        kwargs.setdefault("parent", enclosing_task)
    name = kwargs.pop("name", headers["task"])

    # `heartbeat_interval` isn't a task field; it tells the worker how often to
    # ping while the task runs and may set a `stale_timeout` for it to protect.
    heartbeat_interval, stale_timeout = resolve_heartbeat_options(
        kwargs.pop("heartbeat_interval", None), kwargs.pop("stale_timeout", None), celery_system
    )
    if stale_timeout is not None:
        kwargs["stale_timeout"] = stale_timeout

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
        if heartbeat_interval:
            # Carried on the message so per-call intervals reach the worker.
            headers[TB_HEARTBEAT_INTERVAL] = heartbeat_interval
        if ctask:
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
        items_list = list(items) if not isinstance(items, list | tuple) else items
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

    enter_session(signal_sender)

    delivery_info = getattr(signal_sender.request, "delivery_info", None) or {}
    queue = delivery_info.get("routing_key")
    external_id = signal_sender.request.id
    create_kwargs = {
        "status": StatusEnum.PENDING,
        "data": data,
        "queue": queue,
        "external_id": external_id,
        # eager and canvas tasks are created here rather than at publish time, but
        # still run inside whatever task invoked them
        "parent": parent_id(),
    }
    # `before_task_publish` never ran for these, so per-call options are still
    # sitting in the headers rather than resolved into the message.
    header_kwargs = headers.get(TB_KWARGS_ARG) or {}
    heartbeat_interval, stale_timeout = resolve_heartbeat_options(
        header_kwargs.get("heartbeat_interval", getattr(signal_sender, TB_HEARTBEAT_INTERVAL, None)),
        header_kwargs.get("stale_timeout", getattr(signal_sender, TB_STALE_TIMEOUT, None)),
        celery_system,
    )
    if stale_timeout is not None:
        create_kwargs["stale_timeout"] = stale_timeout
    task = create_task_safe(task_name, **create_kwargs)
    if task:
        # Store the task ID in the request so _update_task can find it
        signal_sender.request.update({TB_TASK_ID: task.id})
        if heartbeat_interval:
            signal_sender.request.update({TB_HEARTBEAT_INTERVAL: heartbeat_interval})
        task_cache.set(task.id, task)


@task_prerun.connect
def task_prerun_handler(sender=None, **kwargs):
    _maybe_create_task(sender)
    _update_task(sender, StatusEnum.PROCESSING)
    _start_heartbeat(sender)
    task_id = _get_taskbadger_task_id(sender.request)
    if task_id:
        # Snapshotted here (same thread as the task body and the failure/retry
        # signals below) so context providers can tell a fresh capture from a
        # stale one if the task errors. The token is restored in
        # task_postrun_handler rather than discarded: a task synchronously
        # invoking another tracked task in its body (eager mode, `.apply()`,
        # canvas primitives) would otherwise leave this task's context
        # clobbered by the inner task's snapshot for the rest of its run.
        token = start_error_context()
        sender.request.update({TB_ERROR_CTX_TOKEN: token})
        # Mark this as the running task so anything it publishes is nested under
        # it. `_update_task` above has already put it in the cache, so this is a
        # lookup rather than a fetch.
        current_token = enter_task(task_id, parent_of(safe_get_task(task_id)))
        sender.request.update({TB_CURRENT_TASK_TOKEN: current_token})


@task_postrun.connect
def task_postrun_handler(sender=None, **kwargs):
    # postrun always fires, unlike the success/failure/retry signals.
    task_id = _get_taskbadger_task_id(sender.request)
    if task_id:
        heartbeat.stop(task_id)
    current_token = sender.request.get(TB_CURRENT_TASK_TOKEN)
    if current_token is not None:
        exit_task(current_token)
        sender.request.update({TB_CURRENT_TASK_TOKEN: None})
    token = sender.request.get(TB_ERROR_CTX_TOKEN)
    if token is not None:
        reset_error_context(token)


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

    enter_session(signal_sender)

    data = None
    if einfo:
        # `einfo.exception` wraps the real exception (see billiard.einfo.ExceptionWithTraceback);
        # unwrap it so context providers (e.g. Sentry) see the original exception.
        exc = getattr(einfo.exception, "exc", einfo.exception)
        data = DefaultMergeStrategy().merge(task.data, capture_error_data(exc, message=str(einfo)))
    task = update_task_safe(task.id, status=status, data=data)
    if task:
        task_cache.set(task_id, task)


def _start_heartbeat(signal_sender):
    """Ping the task periodically for the duration of the run so that tasks
    with a ``stale_timeout`` don't go stale while they're still working.

    The interval is resolved wherever the task was created — at publish time
    for most tasks, in ``_maybe_create_task`` for the rest — so that it always
    matches the ``stale_timeout`` the task was created with.
    """
    request = signal_sender.request
    task_id = _get_taskbadger_task_id(request)
    if not task_id:
        return

    interval = request.get(TB_HEARTBEAT_INTERVAL)
    if interval is None and request.headers:
        interval = request.headers.get(TB_HEARTBEAT_INTERVAL)
    heartbeat.start(task_id, interval)


def enter_session(signal_sender):
    if not Badger.is_configured():
        return
    session = Badger.current.session()
    if session.client:
        # Already open, e.g. an eager task running inside the caller's
        # `taskbadger.Session()`. Not ours, so don't close it either.
        return
    session.__enter__()
    signal_sender.request.update({TB_OWNS_SESSION: True})


def exit_session(signal_sender):
    request = signal_sender.request
    # not `request.headers`: eager tasks carry the ID on the request itself
    # (the task id is checked first so that untracked tasks never touch `Badger`)
    task_id = _get_taskbadger_task_id(request)
    if not task_id or not Badger.is_configured():
        return

    task_cache.unset(task_id)

    if not request.get(TB_OWNS_SESSION):
        return
    request.update({TB_OWNS_SESSION: False})

    session = Badger.current.session()
    if session.client:
        session.__exit__()


def _get_taskbadger_task_id(request):
    if not request:
        return

    task_id = request.get(TB_TASK_ID)
    if task_id:
        return task_id

    if request.headers:
        return request.headers.get(TB_TASK_ID)
