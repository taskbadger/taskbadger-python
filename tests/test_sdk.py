import datetime
from http import HTTPStatus
from unittest import mock

import pytest

from taskbadger import Action, EmailIntegration, StatusEnum, WebhookIntegration, create_task
from taskbadger.exceptions import TaskbadgerException
from taskbadger.internal.models import (
    PatchedTaskRequest,
    TaskRequest,
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
        data=data,
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
        body=request,
    )


def test_before_create_update_task(settings, patched_create):
    def before_create(task):
        tags = task.setdefault("tags", {})
        tags["new"] = "tag"
        return task

    settings.before_create = before_create

    api_task = task_for_test()
    patched_create.return_value = Response(HTTPStatus.OK, b"", {}, api_task)

    task = create_task(name="task name")
    assert task.id == api_task.id

    request = TaskRequest.from_dict(
        {
            "name": "task name",
            "status": StatusEnum.PENDING,
            "tags": {"new": "tag"},
        }
    )
    assert patched_create.call_args[1]["body"] == request


def test_before_create_filter(settings, patched_create):
    def before_create(_):
        return None

    settings.before_create = before_create

    with pytest.raises(TaskbadgerException):
        create_task(name="task name")

    patched_create.assert_not_called()


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


def test_increment_value(settings, patched_update):
    api_task = task_for_test()
    task = Task(api_task)

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(value=10))

    task.increment_value(10)
    _verify_update(settings, patched_update, value=10)

    task.increment_value(5)
    _verify_update(settings, patched_update, value=15)


def test_ping(settings, patched_update):
    task = Task(task_for_test())

    updated_at = task.updated
    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test())
    task.ping(rate_limit=1)
    assert len(patched_update.call_args_list) == 0

    task.ping()
    _verify_update(settings, patched_update)
    assert task.updated > updated_at

    task.ping(rate_limit=1)
    assert len(patched_update.call_args_list) == 1

    task._task.updated = task._task.updated - datetime.timedelta(seconds=1)
    task.ping(rate_limit=1)
    assert len(patched_update.call_args_list) == 2


def test_update_progress_rate_limit(settings, patched_update):
    task = Task(task_for_test(value=1))

    updated_at = task.updated
    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test())
    task.update_value(2, rate_limit=1)
    assert len(patched_update.call_args_list) == 0

    task.update_value(2)
    _verify_update(settings, patched_update, value=2)
    assert task.updated > updated_at

    task.update_value(3, rate_limit=1)
    assert len(patched_update.call_args_list) == 1

    task._task.updated = task._task.updated - datetime.timedelta(seconds=1)
    task.update_value(3, rate_limit=1)
    assert len(patched_update.call_args_list) == 2


def test_update_progress_value_step(settings, patched_update):
    task = Task(task_for_test(value=1))

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(value=4))
    task.update_progress(4, value_step=5)
    assert len(patched_update.call_args_list) == 0

    task.update_progress(4)
    _verify_update(settings, patched_update, value=4)

    task.update_progress(8, value_step=5)
    assert len(patched_update.call_args_list) == 1

    task.update_progress(9, value_step=5)
    assert len(patched_update.call_args_list) == 2


def test_update_progress_min_interval_both(settings, patched_update):
    task = Task(task_for_test(value=1))

    patched_update.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(value=4))
    # neither checks pass
    task.update_progress(4, rate_limit=1, value_step=5)
    assert len(patched_update.call_args_list) == 0

    # value check passes
    task.update_progress(6, rate_limit=1, value_step=5)
    _verify_update(settings, patched_update, value=6)

    # neither checks pass
    task.update_progress(8, rate_limit=1, value_step=5)
    assert len(patched_update.call_args_list) == 1

    # time check passes
    task._task.updated = task._task.updated - datetime.timedelta(seconds=1)
    task.update_progress(6, rate_limit=1, value_step=5)
    assert len(patched_update.call_args_list) == 2


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
        request_params["data"] = kwargs["data"]

    request = PatchedTaskRequest(**request_params)
    if actions:
        request.additional_properties = {"actions": actions}

    # verify expected call
    patched_update.assert_called_with(
        client=mock.ANY,
        organization_slug="org",
        project_slug="project",
        id=mock.ANY,
        body=request,
    )
