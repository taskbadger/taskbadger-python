"""
Note
====

As part of the Celery fixture setup a 'ping' task is run which executes
before the `_bind_settings` fixture is executed. This means that if any code
calls `Badger.is_configured()` (or similar), the `_local` ContextVar in the
Celery runner thread will not have the configuration set.
"""

import logging
from unittest import mock

import celery
import pytest
from kombu.utils.json import register_type

from taskbadger import Action, EmailIntegration, StatusEnum
from taskbadger.celery import Task
from taskbadger.mug import Badger
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_normal(self, a, b):
        assert self.request.get("taskbadger_task") is not None, "missing task in request"
        assert self.taskbadger_task is not None, "missing task on self"
        assert Badger.current.session().client is not None, "missing client"
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task") as get_task,
    ):
        tb_task = task_for_test()
        create.return_value = tb_task
        result = add_normal.delay(2, 2)
        assert result.info.get("taskbadger_task_id") == tb_task.id
        assert result.taskbadger_task_id == tb_task.id
        assert result.get_taskbadger_task() is not None
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once()
    assert get_task.call_count == 2
    assert update.call_count == 2
    assert Badger.current.session().client is None


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_with_args(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_with_task_args(self, a, b):
        assert self.taskbadger_task is not None
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        result = add_with_task_args.apply_async(
            (2, 2),
            taskbadger_name="new_name",
            taskbadger_value_max=10,
            taskbadger_kwargs={"data": {"foo": "bar"}, "tags": {"bar": "baz"}},
        )
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once_with(
        "new_name", value_max=10, data={"foo": "bar"}, tags={"bar": "baz"}, status=StatusEnum.PENDING
    )


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_with_kwargs(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_with_task_args(self, a, b):
        assert self.taskbadger_task is not None
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        actions = [Action("stale", integration=EmailIntegration(to="test@test.com"))]
        result = add_with_task_args.delay(
            2,
            2,
            taskbadger_name="new_name",
            taskbadger_value_max=10,
            taskbadger_kwargs={"actions": actions},
        )
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once_with("new_name", value_max=10, actions=actions, status=StatusEnum.PENDING)


@pytest.mark.usefixtures("_bind_settings")
def test_celery_record_args(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_with_task_args(self, a, b):
        assert self.taskbadger_task is not None
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        result = add_with_task_args.apply_async(
            (2, 2),
            taskbadger_name="new_name",
            taskbadger_value_max=10,
            taskbadger_kwargs={"data": {"foo": "bar"}},
            taskbadger_record_task_args=True,
        )
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once_with(
        "new_name",
        value_max=10,
        data={"foo": "bar", "celery_task_args": [2, 2], "celery_task_kwargs": {}},
        status=StatusEnum.PENDING,
    )


@pytest.mark.usefixtures("_bind_settings")
def test_celery_record_task_kwargs(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_with_task_kwargs(self, a, b, c=0):
        assert self.taskbadger_task is not None
        return a + b + c

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        actions = [Action("stale", integration=EmailIntegration(to="test@test.com"))]
        result = add_with_task_kwargs.delay(
            2,
            2,
            c=3,
            taskbadger_name="new_name",
            taskbadger_value_max=10,
            taskbadger_kwargs={"actions": actions},
            taskbadger_record_task_args=True,
        )
        assert result.get(timeout=10, propagate=True) == 7

    create.assert_called_once_with(
        "new_name",
        value_max=10,
        data={"celery_task_args": [2, 2], "celery_task_kwargs": {"c": 3}},
        actions=actions,
        status=StatusEnum.PENDING,
    )


@pytest.mark.usefixtures("_bind_settings")
def test_celery_record_task_args_custom_serialization(celery_session_app, celery_session_worker):
    class A:
        def __init__(self, a, b):
            self.a = a
            self.b = b

    register_type(A, "A", lambda o: [o.a, o.b], lambda o: A(*o))

    @celery_session_app.task(bind=True, base=Task)
    def add_task_custom_serialization(self, a):
        assert self.taskbadger_task is not None
        return a.a + a.b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        result = add_task_custom_serialization.delay(
            A(2, 2),
            taskbadger_record_task_args=True,
        )
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once_with(
        "tests.test_celery.add_task_custom_serialization",
        data={"celery_task_args": [{"__type__": "A", "__value__": [2, 2]}], "celery_task_kwargs": {}},
        status=StatusEnum.PENDING,
    )


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_with_args_in_decorator(celery_session_app, celery_session_worker):
    @celery_session_app.task(
        bind=True,
        base=Task,
        taskbadger_value_max=10,
        taskbadger_kwargs={"monitor_id": "123"},
    )
    def add_with_task_args_in_decorator(self, a, b):
        assert self.taskbadger_task is not None
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe"),
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        result = add_with_task_args_in_decorator.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once_with(mock.ANY, status=StatusEnum.PENDING, monitor_id="123", value_max=10)


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_retry(celery_session_app, celery_session_worker):
    """Note: When a task is retried, the celery task ID remains the same but a new TB task
    will be created.

    TODO: How to handle this in TB? Should we update the existing TB task or create a new one?
    """

    @celery_session_app.task(bind=True, base=Task)
    def add_retry(self, a, b, is_retry=False):
        assert self.taskbadger_task is not None
        assert Badger.current.session().client is not None
        if not is_retry:
            raise self.retry(kwargs={"is_retry": True}, max_retries=1, countdown=0)

        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task") as get_task,
    ):
        create.return_value = task_for_test()
        get_task.return_value = task_for_test()
        result = add_retry.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    assert create.call_count == 2
    assert update.call_args_list == [
        mock.call(mock.ANY, status=StatusEnum.PROCESSING, data=mock.ANY),
        mock.call(mock.ANY, status=StatusEnum.ERROR, data=mock.ANY),
        mock.call(mock.ANY, status=StatusEnum.PROCESSING, data=mock.ANY),
        mock.call(mock.ANY, status=StatusEnum.SUCCESS, data=mock.ANY),
    ]
    assert Badger.current.session().client is None


def test_celery_task_badger_not_configured(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_no_tb(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            assert Badger.current.session().client is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
    ):
        result = add_no_tb.delay(
            2,
            2,
            taskbadger_kwargs={
                # add an action here to test serialization failure when Badger is not configured
                "actions": [Action("stale", integration=EmailIntegration(to="test@test.com"))]
            },
        )
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_not_called()
    update.assert_not_called()
    assert Badger.current.session().client is None


def test_task_direct_call(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_direct(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            assert Badger.current.session().client is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    assert add_direct(2, 1) == 3
    result = add_direct.apply(args=[2, 3])
    assert result.get(timeout=1, propagate=True) == 5
    assert Badger.current.session().client is None


@pytest.mark.usefixtures("_bind_settings")
def test_task_shared_task(celery_session_worker):
    @celery.shared_task(bind=True, base=Task)
    def add_shared_task(self, a, b):
        assert self.taskbadger_task is not None
        assert Badger.current.session().client is not None
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task"),
    ):
        create.return_value = task_for_test()

        result = add_shared_task.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called()
    update.assert_called()
    assert Badger.current.session().client is None


@pytest.mark.usefixtures("_bind_settings")
def test_task_signature(celery_session_worker):
    @celery.shared_task(bind=True, base=Task)
    def task_signature(self, a):
        assert self.taskbadger_task is not None
        assert Badger.current.session().client is not None
        return a * 2

    celery_session_worker.reload()

    chain = task_signature.s(2) | task_signature.s() | task_signature.s()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task") as get_task,
    ):
        create.return_value = task_for_test()

        result = chain.delay()
        assert result.get(timeout=10, propagate=True) == 16

    assert create.call_count == 3
    assert get_task.call_count == 3
    assert update.call_count == 6
    assert Badger.current.session().client is None


@pytest.mark.usefixtures("_bind_settings")
def test_task_map(celery_session_worker):
    """Tasks executed in a map or starmap are not executed as tasks"""

    @celery.shared_task(bind=True, base=Task)
    def task_map(self, a):
        assert self.taskbadger_task is None
        assert Badger.current.session().client is None
        return a * 2

    celery_session_worker.reload()

    task_map = task_map.map(list(range(5)))

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task") as get_task,
    ):
        result = task_map.delay()
        assert result.get(timeout=10, propagate=True) == [0, 2, 4, 6, 8]

    assert create.call_count == 0
    assert get_task.call_count == 0
    assert update.call_count == 0
    assert Badger.current.session().client is None


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_already_in_terminal_state(celery_session_worker):
    @celery.shared_task(bind=True, base=Task)
    def add_manual_update(self, a, b, is_retry=False):
        # simulate updating the task to a terminal state
        self.request.update({"taskbadger_task": task_for_test(status=StatusEnum.SUCCESS)})
        return a + b

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.celery.get_task") as get_task,
    ):
        create.return_value = task_for_test()

        get_task.return_value = task_for_test()
        result = add_manual_update.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    assert create.call_count == 1
    assert update.call_args_list == [
        mock.call(mock.ANY, status=StatusEnum.PROCESSING, data=mock.ANY),
    ]
