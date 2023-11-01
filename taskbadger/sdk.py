import os
from typing import Any, List

from taskbadger.exceptions import ConfigurationError, ServerError, TaskbadgerException, Unauthorized, UnexpectedStatus
from taskbadger.integrations import Action
from taskbadger.internal.api.task_endpoints import task_create, task_get, task_list, task_partial_update
from taskbadger.internal.models import (
    PatchedTaskRequest,
    PatchedTaskRequestData,
    StatusEnum,
    TaskRequest,
    TaskRequestData,
)
from taskbadger.internal.types import UNSET
from taskbadger.mug import Badger, Session, Settings
from taskbadger.systems import System

_TB_HOST = "https://taskbadger.net"


def init(organization_slug: str = None, project_slug: str = None, token: str = None, systems: List[System] = None):
    """Initialize Task Badger client

    Call this function once per thread
    """
    _init(_TB_HOST, organization_slug, project_slug, token, systems)


def _init(
    host: str = None,
    organization_slug: str = None,
    project_slug: str = None,
    token: str = None,
    systems: List[System] = None,
):
    host = host or os.environ.get("TASKBADGER_HOST", "https://taskbadger.net")
    organization_slug = organization_slug or os.environ.get("TASKBADGER_ORG")
    project_slug = project_slug or os.environ.get("TASKBADGER_PROJECT")
    token = token or os.environ.get("TASKBADGER_API_KEY")

    if host and organization_slug and project_slug and token:
        systems = systems or []
        settings = Settings(
            host, token, organization_slug, project_slug, systems={system.identifier: system for system in systems}
        )
        Badger.current.bind(settings)
    else:
        raise ConfigurationError(
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
    actions: List[Action] = None,
    monitor_id: str = None,
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

    Returns:
        Task: The created Task object.
    """
    value = _none_to_unset(value)
    value_max = _none_to_unset(value_max)
    data = _none_to_unset(data)
    max_runtime = _none_to_unset(max_runtime)
    stale_timeout = _none_to_unset(stale_timeout)

    task = TaskRequest(
        name=name, status=status, value=value, value_max=value_max, max_runtime=max_runtime, stale_timeout=stale_timeout
    )
    scope_data = Badger.current.scope().context
    if scope_data or data:
        data = data or {}
        task.data = TaskRequestData.from_dict({**scope_data, **data})
    if actions:
        task.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(json_body=task)
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
    actions: List[Action] = None,
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

    data = UNSET if not data else PatchedTaskRequestData.from_dict(data)
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
    kwargs = _make_args(id=task_id, json_body=body)
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
        actions: List[Action] = None,
        monitor_id: str = None,
    ) -> "Task":
        """Create a new task"""
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
        """Increment the task progress.
        If the task value is not set it will be set to `amount`.
        """
        value = self._task.value
        value_norm = value if value is not UNSET and value is not None else 0
        new_amount = value_norm + amount
        self.update(value=new_amount)

    def update_progress(self, value: int):
        """Update task progress."""
        self.update(value=value)

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
        actions: List[Action] = None,
        data_merge_strategy: Any = None,
    ):
        """Generic update method used to update any of the task fields.

        This can also be used to add actions.
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
        )
        self._task = task._task

    def add_actions(self, actions: List[Action]):
        """Add actions to the task."""
        self.update(actions=actions)

    def ping(self):
        """Update the task without changing any values. This can be used in conjunction
        with 'stale_timeout' to indicate that the task is still running."""
        self.update()

    @property
    def data(self):
        return self._task.data.additional_properties

    def __getattr__(self, item):
        return getattr(self._task, item)


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
