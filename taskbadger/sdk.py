import dataclasses
from typing import List

from _contextvars import ContextVar
from taskbadger.internal.api.task_endpoints import task_create, tasks_partial_update, task_get
from taskbadger.internal.models import Action, ActionRequest, PatchedTaskRequest, StatusEnum, ActionRequestConfig
from taskbadger.internal.models import Task as CoreTask
from taskbadger.internal.models import TaskData, TaskRequest
from taskbadger.internal.types import UNSET

from taskbadger.internal import AuthenticatedClient

_local = ContextVar("taskbadger_client")


def init(organization_slug: str, project_slug: str, token: str):
    _init("https://taskbadger.net", organization_slug, project_slug, token)


def _init(host: str, organization_slug: str, project_slug: str, token: str):
    client = AuthenticatedClient(host, token, raise_on_unexpected_status=True)
    settings = Settings(client, organization_slug, project_slug)

    _local.set(settings)


def get_task(task_id: str):
    return task_get.sync(**_make_args(id=task_id))


def create_task(
    name: str,
    status: StatusEnum = StatusEnum.PENDING,
    value: int = UNSET,
    data: dict = UNSET,
    actions: List[Action] = None,
) -> CoreTask:
    task = TaskRequest(name=name, status=status, value=value)
    if data:
        task.data = TaskData.from_dict(data)
    if actions:
        task.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(json_body=task)
    response = task_create.sync_detailed(**kwargs)
    return response.parsed


def update_task(
    task_id: str,
    name: str = UNSET,
    status: StatusEnum = UNSET,
    value: int = UNSET,
    data: dict = UNSET,
    actions: List[ActionRequest] = None,
) -> CoreTask:
    body = PatchedTaskRequest.from_dict({"name": name, "status": status, "value": value, "data": data})
    if actions:
        body.additional_properties = {"actions": [a.to_dict() for a in actions]}
    kwargs = _make_args(id=task_id, json_body=body)
    response = tasks_partial_update.sync_detailed(**kwargs)
    return response.parsed


def _make_args(**kwargs):
    settings = _local.get()
    ret_args = dataclasses.asdict(settings)
    ret_args.update(kwargs)
    return ret_args


def _get_settings():
    return _local.get()


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
            data: dict = UNSET,
            actions: List[Action] = None,
    ) -> "Task":
        return Task(
            create_task(name, status, value, data, actions)
        )


class Task(TaskAccessorsMixin):
    def __init__(self, task):
        self._task = task

    def pre_processing(self):
        self.update_status(StatusEnum.PRE_PROCESSING)

    def processing(self, value: int = UNSET):
        self._update(status=StatusEnum.PROCESSING, value=value)

    def post_processing(self, value: int = UNSET):
        self._update(status=StatusEnum.POST_PROCESSING, value=value)

    def success(self, value: int = UNSET):
        self._update(status=StatusEnum.SUCCESS, value=value)

    def error(self, value=UNSET, data: dict = UNSET):
        self._update(status=StatusEnum.ERROR, value=value, data=data)

    def cancel(self):
        self.update_status(StatusEnum.CANCELLED)

    def update_status(self, status: StatusEnum):
        self._update(status=status)

    def increment_progress(self, amount: int):
        self._update(value=self._task.value + amount)

    def update_progress(self, value: int):
        self._update(value=value)

    def update(
            self,
            name: str = UNSET,
            status: StatusEnum = UNSET,
            value: int = UNSET,
            data: dict = UNSET,
            actions: List[ActionRequest] = None,
    ):
        self._update(
            name=name,
            status=status,
            value=value,
            data=data,
            actions=actions
        )

    def add_action(self, integration: str, trigger: str, config: dict = UNSET):
        self._update(actions=[ActionRequest(
            integration=integration,
            trigger=trigger,
            config=ActionRequestConfig.from_dict(config)
        )])

    def _update(self, **kwargs):
        updated_task = update_task(self._task.id, **kwargs)
        self._task = updated_task

    @property
    def data(self):
        return self._task.data.additional_properties

    def __getattr__(self, item):
        return getattr(self._task, item)
