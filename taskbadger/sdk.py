import base64
import datetime
import logging
import os
import warnings
from typing import Any

from taskbadger.exceptions import (
    ConfigurationError,
    MissingConfiguration,
    ServerError,
    TaskbadgerException,
    Unauthorized,
    UnexpectedStatus,
)
from taskbadger.integrations import Action
from taskbadger.internal.api.task_endpoints import (
    task_create,
    task_get,
    task_list,
    task_partial_update,
)
from taskbadger.internal.models import (
    PatchedTaskRequest,
    PatchedTaskRequestTags,
    StatusEnum,
    TaskRequest,
)
from taskbadger.internal.types import UNSET
from taskbadger.mug import Badger, Callback, Session, Settings
from taskbadger.systems import System
from taskbadger.utils import import_string

log = logging.getLogger("taskbadger")

_TB_HOST = "https://taskbadger.net"


def _parse_token(token):
    """Try to decode a project API key.

    Project keys are base64-encoded strings in the format ``org/project/key``.

    Returns:
        A tuple of ``(organization_slug, project_slug, api_key)`` if *token*
        is a valid project key, otherwise ``None``.
    """
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except Exception:
        return None

    parts = decoded.split("/")
    if len(parts) == 3 and all(parts):
        return tuple(parts)
    return None


def init(
    organization_slug: str = None,
    project_slug: str = None,
    token: str = None,
    systems: list[System] = None,
    tags: dict[str, str] = None,
    before_create: Callback = None,
):
    """Initialize Task Badger client.

    If *token* is a project API key (base64-encoded ``org/project/key``),
    the organization and project slugs are extracted automatically and
    *organization_slug* / *project_slug* are ignored.

    For legacy API keys, *organization_slug* and *project_slug* are
    required and a deprecation warning is emitted.

    Call this function once per thread.
    """
    _init(_TB_HOST, organization_slug, project_slug, token, systems, tags, before_create)


def _init(
    host: str = None,
    organization_slug: str = None,
    project_slug: str = None,
    token: str = None,
    systems: list[System] = None,
    tags: dict[str, str] = None,
    before_create: Callback = None,
):
    host = host or os.environ.get("TASKBADGER_HOST", "https://taskbadger.net")
    organization_slug = organization_slug or os.environ.get("TASKBADGER_ORG")
    project_slug = project_slug or os.environ.get("TASKBADGER_PROJECT")
    token = token or os.environ.get("TASKBADGER_API_KEY")

    if token:
        parsed = _parse_token(token)
        if parsed:
            organization_slug, project_slug, token = parsed
        else:
            warnings.warn(
                "Legacy API keys are deprecated. Please switch to a project API key.",
                DeprecationWarning,
                stacklevel=3,
            )

    if before_create and isinstance(before_create, str):
        try:
            before_create = import_string(before_create)
        except ImportError as e:
            raise ConfigurationError(f"Could not import module: {before_create}") from e

    if host and organization_slug and project_slug and token:
        systems = systems or []
        settings = Settings(
            host,
            token,
            organization_slug,
            project_slug,
            systems={system.identifier: system for system in systems},
            before_create=before_create,
        )
        Badger.current.bind(settings, tags)
    else:
        raise MissingConfiguration(
            host=host,
            organization_slug=organization_slug,
            project_slug=project_slug,
            token=token,
        )


def get_task(task_id: str) -> "Task":
    """Fetch a Task from the API based on its ID.

    Arguments:
        task_id: The ID of the task to fetch.
    """
    with Session() as client:
        task = task_get.sync(client=client, **_make_args(id=task_id))
    return Task(task)


def create_task(
    name: str,
    status: StatusEnum = StatusEnum.PENDING,
    value: int = None,
    value_max: int = None,
    data: dict = None,
    max_runtime: int = None,
    stale_timeout: int = None,
    actions: list[Action] = None,
    monitor_id: str = None,
    tags: dict[str, str] = None,
) -> "Task":
    """Create a Task.

    Arguments:
        name: The name of the task.
        status: The task status.
        value: The current 'value' of the task.
        value_max: The maximum value the task is expected to achieve.
        data: Custom task data.
        max_runtime: Maximum expected runtime (seconds).
        stale_timeout: Maximum allowed time between updates (seconds).
        actions: Task actions.
        monitor_id: ID of the monitor to associate this task with.
        tags: Dictionary of namespace -> value tags.

    Returns:
        Task: The created Task object.
    """
    task_dict = {
        "name": name,
        "status": status,
    }
    if value is not None:
        task_dict["value"] = value
    if value_max is not None:
        task_dict["value_max"] = value_max
    if max_runtime is not None:
        task_dict["max_runtime"] = max_runtime
    if stale_timeout is not None:
        task_dict["stale_timeout"] = stale_timeout
    scope = Badger.current.scope()
    if scope.context or data:
        data = data or {}
        task_dict["data"] = {**scope.context, **data}
    if actions:
        task_dict["actions"] = [a.to_dict() for a in actions]
    if scope.tags or tags:
        tags = tags or {}
        task_dict["tags"] = {**scope.tags, **tags}

    task_dict = Badger.current.call_before_create(task_dict)
    if not task_dict:
        raise TaskbadgerException("before_create callback returned None")

    task = TaskRequest.from_dict(task_dict)
    kwargs = _make_args(body=task)
    if monitor_id:
        kwargs["x_taskbadger_monitor"] = monitor_id
    with Session() as client:
        response = task_create.sync_detailed(client=client, **kwargs)
    _check_response(response)
    return Task(response.parsed)


def update_task(
    task_id: str,
    name: str = None,
    status: StatusEnum = None,
    value: int = None,
    value_max: int = None,
    data: dict = None,
    max_runtime: int = None,
    stale_timeout: int = None,
    actions: list[Action] = None,
    tags: dict[str, str] = None,
) -> "Task":
    """Update a task.
    Requires only the task ID and fields to update.

    Arguments:
        task_id: The ID of the task to update.
        name: The name of the task.
        status: The task status.
        value: The current 'value' of the task.
        value_max: The maximum value the task is expected to achieve.
        data: Custom task data.
        max_runtime: Maximum expected runtime (seconds).
        stale_timeout: Maximum allowed time between updates (seconds).
        actions: Task actions.
        tags: Dictionary of namespace -> value tags.

    Returns:
        Task: The updated Task object.
    """
    name = _none_to_unset(name)
    status = _none_to_unset(status)
    value = _none_to_unset(value)
    value_max = _none_to_unset(value_max)
    data = _none_to_unset(data)
    max_runtime = _none_to_unset(max_runtime)
    stale_timeout = _none_to_unset(stale_timeout)

    data = data or UNSET
    body = PatchedTaskRequest(
        name=name,
        status=status,
        value=value,
        value_max=value_max,
        data=data,
        max_runtime=max_runtime,
        stale_timeout=stale_timeout,
    )
    if actions:
        body.additional_properties = {"actions": [a.to_dict() for a in actions]}
    if tags:
        body.tags = PatchedTaskRequestTags.from_dict(tags)
    kwargs = _make_args(id=task_id, body=body)
    with Session() as client:
        response = task_partial_update.sync_detailed(client=client, **kwargs)
    _check_response(response)
    return Task(response.parsed)


def list_tasks(page_size: int = None, cursor: str = None):
    """List tasks."""
    kwargs = _make_args(page_size=page_size, cursor=cursor)
    with Session() as client:
        response = task_list.sync_detailed(client=client, **kwargs)
    _check_response(response)
    return response.parsed


def _make_args(**kwargs):
    settings = Badger.current.settings
    ret_args = settings.as_kwargs()
    ret_args.update(kwargs)
    return ret_args


def _check_response(response):
    if 200 <= response.status_code < 300:
        return response
    elif response.status_code == 401:
        raise Unauthorized("Authentication failed")
    elif response.status_code == 500:
        raise ServerError(response.status_code, response.content)
    else:
        raise UnexpectedStatus(response.status_code, response.content)


class Task:
    """The Task class provides a convenient Python API to interact
    with Task Badger tasks.
    """

    @classmethod
    def get(cls, task_id: str) -> "Task":
        """Get an existing task"""
        return get_task(task_id)

    @classmethod
    def create(
        cls,
        name: str,
        status: StatusEnum = StatusEnum.PENDING,
        value: int = None,
        value_max: int = None,
        data: dict = None,
        max_runtime: int = None,
        stale_timeout: int = None,
        actions: list[Action] = None,
        monitor_id: str = None,
        tags: dict[str, str] = None,
    ) -> "Task":
        """Create a new task

        See [taskbadger.create_task][] for more information.
        """
        return create_task(
            name,
            status,
            value,
            value_max,
            data,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
            actions=actions,
            monitor_id=monitor_id,
            tags=tags,
        )

    def __init__(self, task):
        self._task = task

    def pre_processing(self):
        """Update the task status to `pre_processing`."""
        self.update_status(StatusEnum.PRE_PROCESSING)

    def starting(self):
        """Update the task status to `processing` and set the value to `0`."""
        self.processing(value=0)

    def processing(self, value: int = None):
        """Update the task status to `processing` and set the value."""
        self.update(status=StatusEnum.PROCESSING, value=value)

    def post_processing(self, value: int = None):
        """Update the task status to `post_processing` and set the value."""
        self.update(status=StatusEnum.POST_PROCESSING, value=value)

    def success(self, value: int = None):
        """Update the task status to `success` and set the value."""
        self.update(status=StatusEnum.SUCCESS, value=value)

    def error(self, value: int = None, data: dict = None):
        """Update the task status to `error` and set the value and data."""
        self.update(status=StatusEnum.ERROR, value=value, data=data)

    def canceled(self):
        """Update the task status to `cancelled`"""
        self.update_status(StatusEnum.CANCELLED)

    def update_status(self, status: StatusEnum):
        """Update the task status"""
        self.update(status=status)

    def increment_progress(self, amount: int):
        warnings.warn(
            "'task.increment_progress' will be removed in v1.7.0. Use 'task.increment_value' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.increment_value(amount)

    def increment_value(self, amount: int):
        """Increment the task progress by adding the specified amount to the current value.
        If the task value is not set it will be set to `amount`.
        """
        value = self._task.value
        value_norm = value if value is not UNSET and value is not None else 0
        new_amount = value_norm + amount
        self.update(value=new_amount)

    def update_progress(self, value: int, value_step: int = None, rate_limit: int = None):
        warnings.warn(
            "'task.update_progress' will be removed in v1.7.0. Use 'task.update_value' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.update_value(value, value_step, rate_limit)

    def update_value(self, value: int, value_step: int = None, rate_limit: int = None) -> bool:
        """Update task progress.

        Arguments:
            value: The new value to set.
            value_step: The minimum change in value required to trigger an update.
            rate_limit: The minimum interval between updates in seconds.

        Returns:
            bool: True if the task was updated, False otherwise

        If either `value_step` or `rate_limit` is set, the task will only be updated if the
        specified conditions are met. If both are set, the task will be updated if either
        condition is met.
        """
        skip_check = not (value_step or rate_limit)
        time_check = rate_limit and self._check_update_time_interval(rate_limit)
        value_check = value_step and self._check_update_value_interval(value, value_step)
        if skip_check or time_check or value_check:
            self.update(value=value)
            return True
        return False

    def set_value_max(self, value_max: int):
        """Set the `value_max`."""
        self.update(value_max=value_max)

    def update(
        self,
        name: str = None,
        status: StatusEnum = None,
        value: int = None,
        value_max: int = None,
        data: dict = None,
        max_runtime: int = None,
        stale_timeout: int = None,
        actions: list[Action] = None,
        tags: dict[str, str] = None,
        data_merge_strategy: Any = None,
    ):
        """Generic update method used to update any of the task fields.

        This can also be used to add actions.

        See [taskbadger.update_task][] for more information.
        """
        if data and data_merge_strategy:
            if hasattr(data_merge_strategy, "merge"):
                data = data_merge_strategy.merge(self.data, data)
            elif data_merge_strategy == "default":
                data = DefaultMergeStrategy().merge(self.data, data)
            else:
                raise TaskbadgerException(f"Unknown data_merge_strategy: {data_merge_strategy!r}")

        task = update_task(
            self._task.id,
            name=name,
            status=status,
            value=value,
            value_max=value_max,
            data=data,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
            actions=actions,
            tags=tags,
        )
        self._task = task._task

    def add_actions(self, actions: list[Action]):
        """Add actions to the task."""
        self.update(actions=actions)

    def tag(self, tags: dict[str, str]):
        """Add tags to the task."""
        self.update(tags=tags)

    def ping(self, rate_limit=None) -> bool:
        """Update the task without changing any values. This can be used in conjunction
        with 'stale_timeout' to indicate that the task is still running.

        Arguments:
            rate_limit: The minimum interval between pings in seconds. If set this will only
                update the task if the last update was more than `rate_limit` seconds ago.

        Returns:
            bool: True if the task was updated, False otherwise
        """
        if self._check_update_time_interval(rate_limit):
            self.update()
            return True
        return False

    @property
    def tags(self):
        return self._task.tags.to_dict()

    def __getattr__(self, item):
        return getattr(self._task, item)

    def safe_update(self, **kwargs):
        try:
            self.update(**kwargs)
        except Exception as e:
            log.warning("Error updating task '%s': %s", self._task.id, e)

    def _check_update_time_interval(self, rate_limit: int = None):
        if rate_limit and self._task.updated:
            # tzinfo should always be set but for the sake of safety we check
            if self._task.updated.tzinfo is None:
                tz = None
            else:
                # Use timezone.utc for Python <3.11 compatibility
                tz = datetime.timezone.utc
            now = datetime.datetime.now(tz)
            time_since = now - self._task.updated
            return time_since.total_seconds() >= rate_limit
        return True

    def _check_update_value_interval(self, new_value, value_step: int = None):
        if value_step and self._task.value:
            return new_value - self._task.value >= value_step
        return True


def _none_to_unset(value):
    return UNSET if value is None else value


class DefaultMergeStrategy:
    def __init__(self, append_keys=None):
        self.append_keys = append_keys or []

    def merge(self, existing, new):
        task_data = existing or {}
        for key, value in new.items():
            if key in self.append_keys:
                if key in task_data and value:
                    task_data[key] += value
                elif value:
                    task_data[key] = value
            else:
                task_data[key] = value
        return task_data
