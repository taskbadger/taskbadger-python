import json

import pytest

from taskbadger import Action, EmailIntegration, StatusEnum, update_task
from taskbadger.sdk import _get_settings, create_task, get_task, init


@pytest.fixture(autouse=True)
def init_skd():
    init("org", "project", "token")


@pytest.fixture
def settings():
    return _get_settings()


def test_get_task(httpx_mock):
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/project/tasks/test_id/",
        method="GET",
        match_headers={"Authorization": "Bearer token"},
        json=_json_task_response(),
        status_code=200,
    )

    task = get_task("test_id")
    _verify_task(task)


def test_create_task(httpx_mock):
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/project/tasks/",
        method="POST",
        match_headers={"Authorization": "Bearer token"},
        match_content=b'{"name": "name", "status": "pending"}',
        json=_json_task_response(),
        status_code=201,
    )
    task = create_task("name")
    _verify_task(task)


def test_update_task(httpx_mock):
    expected_body = {
        "name": "new name",
        "status": StatusEnum.SUCCESS,
        "value": 150,
        "value_max": 150,
        "data": {"custom": "value"},
    }
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/project/tasks/test_id/",
        method="PATCH",
        match_headers={"Authorization": "Bearer token"},
        match_content=json.dumps(expected_body).encode("utf8"),
        json=_json_task_response(),
        status_code=200,
    )
    task = update_task(task_id="test_id", **expected_body)
    _verify_task(task)


def test_update_task_actions(httpx_mock):
    expected_body = {"actions": [{"trigger": "success", "integration": "email", "config": {"to": "me@example.com"}}]}
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/project/tasks/test_id/",
        method="PATCH",
        match_headers={"Authorization": "Bearer token"},
        match_content=json.dumps(expected_body).encode("utf8"),
        json=_json_task_response(),
        status_code=200,
    )
    task = update_task(task_id="test_id", actions=[Action("success", EmailIntegration("me@example.com"))])
    _verify_task(task)


def _json_task_response(**kwargs):
    response = {
        "id": "test_id",
        "organization": "org",
        "project": "project",
        "name": "demo task",
        "status": "pending",
        "value": None,
        "value_max": 100,
        "value_percent": None,
        "data": {"custom": "value"},
        "created": "2022-09-22T06:53:40.683555Z",
        "updated": "2022-09-22T06:53:40.683555Z",
        "url": None,
        "public_url": None,
    }
    response.update(kwargs)
    return response


def _verify_task(task, **kwargs):
    expected = _json_task_response(**kwargs)
    assert task.id == expected["id"]
    assert task.organization == expected["organization"]
    assert task.project == expected["project"]
    assert task.name == expected["name"]
    assert task.status == expected["status"]
    assert task.value == expected["value"]
    assert task.value_max == expected["value_max"]
    assert task.value_percent == expected["value_percent"]
    assert task.data == expected["data"]
