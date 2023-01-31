import dataclasses
import os
from typing import List

from _contextvars import ContextVar

from taskbadger import Action
from taskbadger.exceptions import ConfigurationError
from taskbadger.internal import AuthenticatedClient, errors
from taskbadger.internal.api.task_endpoints import task_create, task_get, task_partial_update
from taskbadger.internal.models import PatchedTaskRequest, PatchedTaskRequestData, StatusEnum
from taskbadger.internal.models import Task as CoreTask
from taskbadger.internal.models import TaskData, TaskRequest
from taskbadger.internal.types import UNSET

_local = ContextVar("taskbadger_client")


def init(organization_slug: str = None, project_slug: str = None, token: str = None):
    _init("https://taskbadger.net", organization_slug, project_slug, token)


def _init(host: str = None, organization_slug: str = None, project_slug: str = None, token: str = None):
    host = host or os.environ.get("TASKBADGER_HOST", "https://taskbadger.net")
    organization_slug = organization_slug or os.environ.get("TASKBADGER_ORG")
    project_slug = project_slug or os.environ.get("TASKBADGER_PROJECT")
    token = token or os.environ.get("TASKBADGER_TOKEN")

    if host and organization_slug and project_slug and token:
        client = AuthenticatedClient(host, token)
        settings = Settings(client, organization_slug, project_slug)
        _local.set(settings)
    else:
        raise ConfigurationError(
            host=host,
            organization_slug=organization_slug,
            project_slug=project_slug,
            token=token,
        )


def get_task(task_id: str):
    return task_get.sync(**_make_args(id=task_id))


def create_task(
    name: str,
    status: StatusEnum = StatusEnum.PENDING,
    value: int = UNSET,
    value_max: int = UNSET,
    data: dict = UNSET,
    actions: List[Action] = None,
) -> CoreTask:
    task = TaskRequest(name=name, status=status, value=value, value_max=value_max)
    if data:
        task.data = TaskData.from_dict(data)
    if actions:
        task.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(json_body=task)
    response = task_create.sync_detailed(**kwargs)
    _check_response(response)
    return response.parsed


def update_task(
    task_id: str,
    name: str = UNSET,
    status: StatusEnum = UNSET,
    value: int = UNSET,
    value_max: int = UNSET,
    data: dict = UNSET,
    actions: List[Action] = None,
) -> CoreTask:
    data = UNSET if data is UNSET else PatchedTaskRequestData.from_dict(data)
    body = PatchedTaskRequest(name=name, status=status, value=value, value_max=value_max, data=data)
    if actions:
        body.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(id=task_id, json_body=body)
    response = task_partial_update.sync_detailed(**kwargs)
    _check_response(response)
    return response.parsed


def _make_args(**kwargs):
    settings = _local.get()
    ret_args = dataclasses.asdict(settings)
    ret_args.update(kwargs)
    return ret_args


def _get_settings():
    return _local.get()


def _check_response(response):
    if 200 <= response.status_code < 300:
        return response

    else:
        raise errors.UnexpectedStatus(f"Unexpected status code: {response.status_code}", response.content)


@dataclasses.dataclass
class Settings:
    client: AuthenticatedClient
    organization_slug: str
    project_slug: str


class TaskAccessorsMixin:
    @classmethod
    def get(cls, task_id: str) -> "Task":
        return Task(get_task(task_id))

    @classmethod
    def create(
        cls,
        name: str,
        status: StatusEnum = StatusEnum.PENDING,
        value: int = UNSET,
        value_max: int = UNSET,
        data: dict = UNSET,
        actions: List[Action] = None,
    ) -> "Task":
        return Task(create_task(name, status, value, value_max, data, actions))


class Task(TaskAccessorsMixin):
    def __init__(self, task):
        self._task = task

    def pre_processing(self):
        self.update_status(StatusEnum.PRE_PROCESSING)

    def start(self):
        self.processing(value=0)

    def processing(self, value: int = UNSET):
        self.update(status=StatusEnum.PROCESSING, value=value)

    def post_processing(self, value: int = UNSET):
        self.update(status=StatusEnum.POST_PROCESSING, value=value)

    def success(self, value: int = UNSET):
        self.update(status=StatusEnum.SUCCESS, value=value)

    def error(self, value: int = UNSET, data: dict = UNSET):
        self.update(status=StatusEnum.ERROR, value=value, data=data)

    def cancel(self):
        self.update_status(StatusEnum.CANCELLED)

    def update_status(self, status: StatusEnum):
        self.update(status=status)

    def increment_progress(self, amount: int):
        self.update(value=self._task.value + amount)

    def update_progress(self, value: int):
        self.update(value=value)

    def set_value_max(self, value_max: int):
        self.update(value_max=value_max)

    def update(
        self,
        name: str = UNSET,
        status: StatusEnum = UNSET,
        value: int = UNSET,
        value_max: int = UNSET,
        data: dict = UNSET,
        actions: List[Action] = None,
    ):
        self._task = update_task(
            self._task.id, name=name, status=status, value=value, value_max=value_max, data=data, actions=actions
        )

    def add_actions(self, actions: List[Action]):
        self.update(actions=actions)

    @property
    def data(self):
        return self._task.data.additional_properties

    def __getattr__(self, item):
        return getattr(self._task, item)
