from unittest import mock

import celery
import pytest

from taskbadger import StatusEnum
from taskbadger.celery import Task
from taskbadger.mug import Badger, Settings
from tests.utils import task_for_test


@pytest.fixture
def bind_settings():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))
    yield
    Badger.current.bind(None)


def test_celery_task(celery_session_app, celery_session_worker, bind_settings):
    @celery_session_app.task(bind=True, base=Task)
    def add_normal(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.request.get("taskbadger_task") is None

            assert self.taskbadger_task is not None
            assert self.request.get("taskbadger_task") is not None
            get_task.assert_called_once()

            # check that the task is cached
            assert self.taskbadger_task is not None
            get_task.assert_called_once()

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update:
        result = add_normal.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called()
    update.assert_called()


def test_celery_task_error(celery_session_app, celery_session_worker, bind_settings):
    @celery_session_app.task(bind=True, base=Task)
    def add_error(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            get_task.return_value = task_for_test()
            assert self.taskbadger_task is not None
        raise Exception("error")

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update:
        result = add_error.delay(2, 2)
        with pytest.raises(Exception):
            result.get(timeout=10, propagate=True)

    create.assert_called()
    update.assert_called_with(mock.ANY, status=StatusEnum.ERROR, data=mock.ANY)
    data_kwarg = update.call_args_list[0][1]["data"]
    assert "Traceback" in data_kwarg["exception"]


def test_celery_task_retry(celery_session_app, celery_session_worker, bind_settings):
    @celery_session_app.task(bind=True, base=Task)
    def add_retry(self, a, b, is_retry=False):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            get_task.return_value = task_for_test()
            assert self.taskbadger_task is not None
        if not is_retry:
            raise self.retry(kwargs={"is_retry": True}, max_retries=1, countdown=0)

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update:
        result = add_retry.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    assert create.call_count == 2
    assert update.call_args_list == [
        mock.call(mock.ANY, status=StatusEnum.ERROR, data=mock.ANY),
        mock.call(mock.ANY, status=StatusEnum.SUCCESS, data=mock.ANY),
    ]


def test_celery_task_badger_not_configured(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_no_tb(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update:
        result = add_no_tb.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_not_called()
    update.assert_not_called()


def test_task_direct_call(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_direct(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    assert add_direct(2, 1) == 3
    result = add_direct.apply(args=[2, 3])
    assert result.get(timeout=1, propagate=True) == 5


def test_task_shared_task(celery_session_worker, bind_settings):
    @celery.shared_task(bind=True, base=Task)
    def add_shared_task(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task is not None
            get_task.assert_called()

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update:
        result = add_shared_task.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called()
    update.assert_called()
