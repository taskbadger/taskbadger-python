from datetime import datetime
from http import HTTPStatus
from unittest import mock

import pytest

from taskbadger import Action, EmailIntegration, StatusEnum
from taskbadger.internal.models import PatchedTaskRequest, PatchedTaskRequestData
from taskbadger.internal.models import Task as TaskInternal
from taskbadger.internal.models import TaskData, TaskRequest, TaskRequestData
from taskbadger.internal.types import UNSET, Response
from taskbadger.sdk import Task, _get_settings, init


@pytest.fixture(autouse=True)
def init_skd():
    init("org", "project", "token")


@pytest.fixture
def settings():
    return _get_settings()


@pytest.fixture
def patched_get():
    with mock.patch("taskbadger.sdk.task_get.sync") as get:
        yield get


@pytest.fixture
def patched_create():
    with mock.patch("taskbadger.sdk.task_create.sync_detailed") as create:
        yield create


@pytest.fixture
def patched_update():
    with mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as update:
        yield update


def test_get(patched_get):
    data = {"a": 1}
    api_task = _task_for_test(data=data)
    patched_get.return_value = api_task
    fetched_task = Task.get("test_id")
    assert fetched_task.id == api_task.id
    assert fetched_task.data == data


def test_create(settings, patched_create):
    api_task = _task_for_test()
    patched_create.return_value = Response(HTTPStatus.OK, b"", {}, api_task)

    action = Action("success", integration=EmailIntegration(to="me@example.com"))
    data = {"a": 1}
    task = Task.create(name="task name", status=StatusEnum.PRE_PROCESSING, value=13, data=data, actions=[action])
    assert task.id == api_task.id

    request = TaskRequest(
        name="task name",
        status=StatusEnum.PRE_PROCESSING,
        value=13,
        value_max=UNSET,
        data=TaskRequestData.from_dict(data),
    )
    request.additional_properties = {
        "actions": [{"trigger": "success", "integration": "email", "config": {"to": "me@example.com"}}]
    }
    patched_create.assert_called_with(
        client=settings.client, organization_slug="org", project_slug="project", json_body=request
    )


def test_update_status(settings, patched_update):
    api_task = _task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)
    task.update_status(StatusEnum.PRE_PROCESSING)

    # expected request
    _verify_update(settings, patched_update, status=StatusEnum.PRE_PROCESSING)


def test_update_data(settings, patched_update):
    api_task = _task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)
    task.update(data={"a": 1})

    # expected request
    _verify_update(settings, patched_update, data={"a": 1})


def test_increment_progress(settings, patched_update):
    api_task = _task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, _task_for_test(value=10))

    task.increment_progress(10)
    _verify_update(settings, patched_update, value=10)

    task.increment_progress(10)
    _verify_update(settings, patched_update, value=20)


def test_add_actions(settings, patched_update):
    api_task = TaskInternal("test_id", "org", "project", "task_name", datetime.utcnow(), datetime.utcnow(), None)
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, api_task)

    action = Action("*/10%,success,error", integration=EmailIntegration(to="me@example.com"))
    task.add_actions([action])

    # expected request
    _verify_update(
        settings,
        patched_update,
        actions=[{"trigger": "*/10%,success,error", "integration": "email", "config": {"to": "me@example.com"}}],
    )


def _task_for_test(**kwargs):
    data = kwargs.pop("data", None)
    if data:
        kwargs["data"] = TaskData.from_dict(data)
    return TaskInternal("test_id", "org", "project", "task_name", datetime.utcnow(), datetime.utcnow(), None, **kwargs)


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
        client=settings.client, organization_slug="org", project_slug="project", id="test_id", json_body=request
    )
