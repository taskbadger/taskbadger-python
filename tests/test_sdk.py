from http import HTTPStatus
from unittest import mock

import pytest

from taskbadger import Action, EmailIntegration, StatusEnum, WebhookIntegration
from taskbadger.exceptions import TaskbadgerException
from taskbadger.internal.models import (
    PatchedTaskRequest,
    PatchedTaskRequestData,
    TaskRequest,
    TaskRequestData,
)
from taskbadger.internal.types import UNSET, Response
from taskbadger.mug import Badger
from taskbadger.sdk import Task, init
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _init_skd():
    init("org", "project", "token")


@pytest.fixture()
def settings():
    return Badger.current.settings


@pytest.fixture()
def patched_get():
    with mock.patch("taskbadger.sdk.task_get.sync") as get:
        yield get


@pytest.fixture()
def patched_create():
    with mock.patch("taskbadger.sdk.task_create.sync_detailed") as create:
        yield create


@pytest.fixture()
def patched_update():
    with mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as update:
        yield update


def test_get(patched_get):
    data = {"a": 1}
    api_task = task_for_test(data=data)
    patched_get.return_value = api_task
    fetched_task = Task.get("test_id")
    assert fetched_task.id == api_task.id
    assert fetched_task.data == data


def test_create(settings, patched_create):
    api_task = task_for_test()
    patched_create.return_value = Response(HTTPStatus.OK, b"", {}, api_task)

    action = Action("success", integration=EmailIntegration(to="me@example.com"))
    data = {"a": 1}
    task = Task.create(
        name="task name",
        status=StatusEnum.PRE_PROCESSING,
        value=13,
        data=data,
        max_runtime=10,
        stale_timeout=2,
        actions=[action],
    )
    assert task.id == api_task.id

    request = TaskRequest(
        name="task name",
        status=StatusEnum.PRE_PROCESSING,
        value=13,
        value_max=UNSET,
        data=TaskRequestData.from_dict(data),
        max_runtime=10,
        stale_timeout=2,
    )
    request.additional_properties = {
        "actions": [
            {
                "trigger": "success",
                "integration": "email",
                "config": {"to": "me@example.com"},
            }
        ]
    }
    patched_create.assert_called_with(
        client=mock.ANY,
        organization_slug="org",
        project_slug="project",
        json_body=request,
    )


def test_update_status(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)
    task.update_status(StatusEnum.PRE_PROCESSING)

    # expected request
    _verify_update(settings, patched_update, status=StatusEnum.PRE_PROCESSING)


def test_update_data(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)
    task.update(data={"a": 1})

    # expected request
    _verify_update(settings, patched_update, data={"a": 1})


def test_increment_progress(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(value=10))

    task.increment_progress(10)
    _verify_update(settings, patched_update, value=10)

    task.increment_progress(10)
    _verify_update(settings, patched_update, value=20)


def test_update_timeouts(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(max_runtime=10, stale_timeout=2))

    task.update(max_runtime=10, stale_timeout=2)
    _verify_update(settings, patched_update, max_runtime=10, stale_timeout=2)


def test_add_actions(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)

    task.add_actions(
        [
            Action("*/10%,success,error", integration=EmailIntegration(to="me@example.com")),
            Action("cancelled", integration=WebhookIntegration(id="webhook:123")),
        ]
    )

    # expected request
    _verify_update(
        settings,
        patched_update,
        actions=[
            {
                "trigger": "*/10%,success,error",
                "integration": "email",
                "config": {"to": "me@example.com"},
            },
            {"trigger": "cancelled", "integration": "webhook:123", "config": {}},
        ],
    )


def test_action_validation():
    WebhookIntegration(id="webhook:123")
    with pytest.raises(TaskbadgerException):
        WebhookIntegration(id="email:123")


def _verify_update(settings, patched_update, **kwargs):
    actions = kwargs.pop("actions", None)
    request_params = {
        "name": UNSET,
        "status": UNSET,
        "value": UNSET,
        "value_max": UNSET,
        "data": UNSET,
    }
    request_params.update(kwargs)

    if kwargs.get("data"):
        request_params["data"] = PatchedTaskRequestData.from_dict(kwargs["data"])

    request = PatchedTaskRequest(**request_params)
    if actions:
        request.additional_properties = {"actions": actions}

    # verify expected call
    patched_update.assert_called_with(
        client=mock.ANY,
        organization_slug="org",
        project_slug="project",
        id=mock.ANY,
        json_body=request,
    )
