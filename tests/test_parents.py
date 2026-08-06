"""Tests for parent/child task nesting.

Tasks nest a single level deep. A task created while another one is running is
attached to it via `parent`; if the running task is itself a child, the new task
is attached to the same root rather than to the child.
"""

import logging
from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

# imported as a module, not by name: `test_celery_system_integration` drops
# `taskbadger.celery` from `sys.modules` and lets it be re-imported, so anything
# bound at import time can end up referring to a stale module object that
# `mock.patch` no longer reaches
import taskbadger.celery
from taskbadger import StatusEnum, track
from taskbadger._current_task import current_task_id, enter_task, exit_task, parent_id
from taskbadger.procrastinate import _instrument_task
from taskbadger.sdk import Task, create_task, list_tasks, update_task
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


@pytest.fixture
def app():
    app = procrastinate.App(connector=testing.InMemoryConnector())
    with app.open():
        yield app


def _json_task_response(**kwargs):
    response = {
        "id": "test_id",
        "organization": "org",
        "project": "proj",
        "name": "demo task",
        "status": "pending",
        "value": None,
        "value_max": 100,
        "value_percent": None,
        "data": None,
        "created": "2022-09-22T06:53:40.683555Z",
        "updated": "2022-09-22T06:53:40.683555Z",
        "url": None,
        "public_url": None,
        "tags": {},
    }
    response.update(kwargs)
    return response


# --- the ambient current-task record -----------------------------------------


def test_no_parent_outside_a_tracked_task():
    assert current_task_id() is None
    assert parent_id() is None


def test_tasks_created_while_a_root_task_runs_nest_under_it():
    token = enter_task("root")
    try:
        assert current_task_id() == "root"
        assert parent_id() == "root"
    finally:
        exit_task(token)
    assert current_task_id() is None
    assert parent_id() is None


def test_grandchildren_are_flattened_onto_the_root():
    root = enter_task("root")
    child = enter_task("child", parent="root")
    try:
        # the child is what's running, but nesting stops at one level so anything
        # it creates joins it under the root instead of hanging off it
        assert current_task_id() == "child"
        assert parent_id() == "root"
    finally:
        exit_task(child)
        exit_task(root)


# --- the SDK surface ----------------------------------------------------------


@pytest.mark.usefixtures("_bind_settings")
def test_create_task_sends_parent(httpx_mock):
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/proj/tasks/",
        method="POST",
        match_json={"name": "child", "status": "pending", "parent": "parent_id"},
        json=_json_task_response(parent="parent_id"),
        status_code=201,
    )
    task = create_task("child", parent="parent_id")
    assert task.parent == "parent_id"


@pytest.mark.usefixtures("_bind_settings")
def test_task_create_sends_parent(httpx_mock):
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/proj/tasks/",
        method="POST",
        match_json={"name": "child", "status": "pending", "parent": "parent_id"},
        json=_json_task_response(parent="parent_id"),
        status_code=201,
    )
    assert Task.create("child", parent="parent_id").parent == "parent_id"


@pytest.mark.usefixtures("_bind_settings")
def test_update_task_sends_parent(httpx_mock):
    """The API allows setting a parent on a task that doesn't have one yet."""
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/proj/tasks/test_id/",
        method="PATCH",
        match_json={"parent": "parent_id"},
        json=_json_task_response(parent="parent_id"),
        status_code=200,
    )
    assert update_task("test_id", parent="parent_id").parent == "parent_id"


@pytest.mark.usefixtures("_bind_settings")
def test_list_tasks_filters_by_parent(httpx_mock):
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/proj/tasks/?parent=parent_id",
        method="GET",
        json={"next": None, "previous": None, "results": [_json_task_response(parent="parent_id")]},
        status_code=200,
    )
    (child,) = list_tasks(parent="parent_id").results
    assert child.parent == "parent_id"


@pytest.mark.usefixtures("_bind_settings")
def test_create_task_omits_parent_when_not_given(httpx_mock):
    """A bare `create_task` stays top-level even inside a running task — only the
    integrations nest automatically."""
    httpx_mock.add_response(
        url="https://taskbadger.net/api/org/proj/tasks/",
        method="POST",
        match_json={"name": "solo", "status": "pending"},
        json=_json_task_response(),
        status_code=201,
    )
    token = enter_task("root")
    try:
        create_task("solo")
    finally:
        exit_task(token)


# --- the @track decorator -----------------------------------------------------


@mock.patch("taskbadger.decorators._update_safe")
@mock.patch("taskbadger.decorators.create_task_safe")
def test_track_makes_its_task_current(create, update):
    create.return_value = task_for_test(id="outer_id")
    seen = {}

    @track
    def outer():
        seen["parent"] = parent_id()

    outer()

    assert "parent" not in create.call_args.kwargs
    assert seen["parent"] == "outer_id"


@mock.patch("taskbadger.decorators._update_safe")
@mock.patch("taskbadger.decorators.create_task_safe")
def test_track_nests_under_an_enclosing_tracked_task(create, update):
    create.side_effect = [task_for_test(id="outer_id"), task_for_test(id="inner_id", parent="outer_id")]

    @track
    def inner():
        pass

    @track
    def outer():
        inner()

    outer()

    assert create.call_args_list[1].kwargs["parent"] == "outer_id"


@mock.patch("taskbadger.decorators._update_safe")
@mock.patch("taskbadger.decorators.create_task_safe")
def test_track_explicit_parent_wins(create, update):
    create.return_value = task_for_test(id="outer_id")

    @track(parent="chosen")
    def inner():
        pass

    token = enter_task("root")
    try:
        inner()
    finally:
        exit_task(token)

    assert create.call_args.kwargs["parent"] == "chosen"


# --- Celery -------------------------------------------------------------------


def _publish(name="child.task", **headers):
    headers = {"id": "abc123", "task": name, "taskbadger_track": True, **headers}
    taskbadger.celery.task_publish_handler(sender=name, headers=headers, body=[[], {}, {}])


@pytest.mark.usefixtures("_bind_settings")
def test_celery_publish_nests_under_the_running_task():
    with mock.patch("taskbadger.celery.create_task_safe") as create:
        create.return_value = task_for_test()
        token = enter_task("root_id")
        try:
            _publish()
        finally:
            exit_task(token)

    assert create.call_args.kwargs["parent"] == "root_id"


@pytest.mark.usefixtures("_bind_settings")
def test_celery_publish_flattens_grandchildren():
    with mock.patch("taskbadger.celery.create_task_safe") as create:
        create.return_value = task_for_test()
        root = enter_task("root_id")
        child = enter_task("child_id", parent="root_id")
        try:
            _publish()
        finally:
            exit_task(child)
            exit_task(root)

    assert create.call_args.kwargs["parent"] == "root_id"


@pytest.mark.usefixtures("_bind_settings")
def test_celery_publish_has_no_parent_outside_a_task():
    with mock.patch("taskbadger.celery.create_task_safe") as create:
        create.return_value = task_for_test()
        _publish()

    assert "parent" not in create.call_args.kwargs


@pytest.mark.usefixtures("_bind_settings")
def test_celery_publish_explicit_parent_wins():
    with mock.patch("taskbadger.celery.create_task_safe") as create:
        create.return_value = task_for_test()
        token = enter_task("root_id")
        try:
            _publish(**{taskbadger.celery.TB_KWARGS_ARG: {"parent": "chosen"}})
        finally:
            exit_task(token)

    assert create.call_args.kwargs["parent"] == "chosen"


# --- Procrastinate ------------------------------------------------------------


@pytest.mark.usefixtures("_bind_settings")
def test_procrastinate_defer_nests_under_the_running_task(app):
    @app.task(name="child")
    def child(x):
        return x

    _instrument_task(child, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe") as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
    ):
        create.return_value = task_for_test(id="child_tb")
        token = enter_task("root_id")
        try:
            child.defer(x=1)
        finally:
            exit_task(token)

    assert create.call_args.kwargs["parent"] == "root_id"


@pytest.mark.usefixtures("_bind_settings")
def test_procrastinate_defer_has_no_parent_outside_a_task(app):
    @app.task(name="solo")
    def solo(x):
        return x

    _instrument_task(solo, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe") as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
    ):
        create.return_value = task_for_test(id="solo_tb")
        solo.defer(x=1)

    assert "parent" not in create.call_args.kwargs


@pytest.mark.usefixtures("_bind_settings")
def test_procrastinate_worker_makes_its_task_current(app):
    """The worker side marks the running job's task as current so anything it
    defers nests under it."""
    seen = {}

    @app.task(name="records_parent")
    def records_parent():
        seen["parent"] = parent_id()

    _instrument_task(records_parent, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.sdk.get_task") as get,
    ):
        update.return_value = task_for_test(id="job_tb", status=StatusEnum.PROCESSING)
        get.return_value = update.return_value
        records_parent.func(**{"__taskbadger_task_id__": "job_tb"})

    assert seen["parent"] == "job_tb"
    assert current_task_id() is None
