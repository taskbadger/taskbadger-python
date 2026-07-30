"""Tests for the automatic heartbeat that keeps running Celery tasks fresh.

See the note in ``test_celery.py`` about the Celery fixture setup.
"""

import logging
import time
from unittest import mock

import pytest

import taskbadger
from taskbadger import StatusEnum
from taskbadger.celery import Task
from taskbadger.mug import Badger, Settings
from taskbadger.systems.celery import CelerySystemIntegration
from tests.utils import task_for_test


def _wait_for_call_count(mock_obj, expected, timeout=10.0):
    deadline = time.monotonic() + timeout
    while mock_obj.call_count < expected and time.monotonic() < deadline:
        time.sleep(0.01)


@pytest.fixture
def _bind_settings_with_heartbeat():
    systems = [CelerySystemIntegration(heartbeat_interval=5)]
    Badger.current.bind(
        Settings(
            "https://taskbadger.net",
            "token",
            "org",
            "proj",
            systems={system.identifier: system for system in systems},
        )
    )
    yield
    Badger.current.bind(None)


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


@pytest.fixture
def heartbeat():
    with mock.patch("taskbadger.celery.heartbeat") as heartbeat:
        yield heartbeat


@pytest.mark.usefixtures("_bind_settings_with_heartbeat")
def test_heartbeat_from_system_integration(celery_session_app, celery_session_worker, heartbeat):
    @celery_session_app.task
    def add_auto_heartbeat(a, b):
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task"),
    ):
        tb_task = task_for_test()
        create.return_value = tb_task
        assert add_auto_heartbeat.delay(2, 2).get(timeout=10, propagate=True) == 4
        _wait_for_call_count(heartbeat.stop, 1)

    create.assert_called_once_with(
        "tests.test_celery_heartbeat.add_auto_heartbeat",
        status=StatusEnum.PENDING,
        queue="celery",
        external_id=mock.ANY,
        stale_timeout=10,
    )
    heartbeat.start.assert_called_once_with(tb_task.id, 5)
    heartbeat.stop.assert_called_once_with(tb_task.id)


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_from_task_option(celery_session_app, celery_session_worker, heartbeat):
    @celery_session_app.task(base=Task, taskbadger_heartbeat_interval=7)
    def add_task_heartbeat(a, b):
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task"),
    ):
        tb_task = task_for_test()
        create.return_value = tb_task
        assert add_task_heartbeat.delay(2, 2).get(timeout=10, propagate=True) == 4
        _wait_for_call_count(heartbeat.stop, 1)

    assert create.call_args.kwargs["stale_timeout"] == 14
    heartbeat.start.assert_called_once_with(tb_task.id, 7)
    heartbeat.stop.assert_called_once_with(tb_task.id)


@pytest.mark.usefixtures("_bind_settings_with_heartbeat")
def test_heartbeat_from_apply_async_overrides_system(celery_session_app, celery_session_worker, heartbeat):
    # per-call options are only picked up by tasks using the `Task` base class
    @celery_session_app.task(base=Task)
    def add_call_heartbeat(a, b):
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task"),
    ):
        tb_task = task_for_test()
        create.return_value = tb_task
        result = add_call_heartbeat.apply_async((2, 2), taskbadger_heartbeat_interval=3, taskbadger_stale_timeout=30)
        assert result.get(timeout=10, propagate=True) == 4
        _wait_for_call_count(heartbeat.stop, 1)

    assert create.call_args.kwargs["stale_timeout"] == 30
    heartbeat.start.assert_called_once_with(tb_task.id, 3)


@pytest.mark.usefixtures("_bind_settings_with_heartbeat")
def test_heartbeat_for_eager_task(celery_session_app, heartbeat):
    """Eager tasks are created worker-side by ``_maybe_create_task``."""

    @celery_session_app.task(base=Task)
    def add_eager(a, b):
        return a + b

    celery_session_app.conf.task_always_eager = True
    try:
        with (
            mock.patch("taskbadger.celery.create_task_safe") as create,
            mock.patch("taskbadger.celery.update_task_safe"),
            mock.patch("taskbadger.sdk.get_task"),
        ):
            tb_task = task_for_test()
            create.return_value = tb_task
            assert add_eager.delay(2, 2).get(timeout=10, propagate=True) == 4
    finally:
        celery_session_app.conf.task_always_eager = False

    assert create.call_args.kwargs["stale_timeout"] == 10
    heartbeat.start.assert_called_once_with(tb_task.id, 5)
    heartbeat.stop.assert_called_once_with(tb_task.id)


@pytest.mark.usefixtures("_bind_settings_with_heartbeat")
def test_heartbeat_for_eager_task_from_apply_async(celery_session_app, heartbeat):
    """``before_task_publish`` doesn't run for eager tasks, so the per-call
    options have to be read back out of the headers."""

    @celery_session_app.task(base=Task)
    def add_eager_options(a, b):
        return a + b

    celery_session_app.conf.task_always_eager = True
    try:
        with (
            mock.patch("taskbadger.celery.create_task_safe") as create,
            mock.patch("taskbadger.celery.update_task_safe"),
            mock.patch("taskbadger.sdk.get_task"),
        ):
            tb_task = task_for_test()
            create.return_value = tb_task
            result = add_eager_options.apply_async((2, 2), taskbadger_heartbeat_interval=3)
            assert result.get(timeout=10, propagate=True) == 4
    finally:
        celery_session_app.conf.task_always_eager = False

    assert create.call_args.kwargs["stale_timeout"] == 6
    heartbeat.start.assert_called_once_with(tb_task.id, 3)


@pytest.mark.usefixtures("_bind_settings_with_heartbeat")
def test_eager_task_leaves_an_open_session_alone(celery_session_app, heartbeat):
    """An eager task must not close a session opened by its caller."""

    @celery_session_app.task(base=Task)
    def add_in_session(a, b):
        return a + b

    celery_session_app.conf.task_always_eager = True
    try:
        with (
            mock.patch("taskbadger.celery.create_task_safe", return_value=task_for_test()),
            mock.patch("taskbadger.celery.update_task_safe", return_value=task_for_test()),
            mock.patch("taskbadger.sdk.get_task"),
            mock.patch("taskbadger.mug.AuthenticatedClient"),
        ):
            with taskbadger.Session():
                session = Badger.current.session()
                assert add_in_session.delay(2, 2).get(timeout=10, propagate=True) == 4
                assert session.client is not None, "the caller's session was closed by the task"
            assert session.client is None
    finally:
        celery_session_app.conf.task_always_eager = False


@pytest.mark.usefixtures("_bind_settings")
def test_no_heartbeat_by_default(celery_session_app, celery_session_worker, heartbeat):
    @celery_session_app.task(base=Task)
    def add_no_heartbeat(a, b):
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.sdk.get_task"),
    ):
        create.return_value = task_for_test()
        assert add_no_heartbeat.delay(2, 2).get(timeout=10, propagate=True) == 4
        _wait_for_call_count(update, 2)

    assert "stale_timeout" not in create.call_args.kwargs
    heartbeat.start.assert_called_once_with(mock.ANY, None)
