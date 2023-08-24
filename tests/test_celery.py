from unittest import mock

import celery
import pytest

from taskbadger.celery import Task
from taskbadger.mug import Badger, Settings


@pytest.fixture
def bind_settings():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))
    yield
    Badger.current.bind(None)


def test_celery_task(celery_session_app, celery_session_worker, bind_settings):
    @celery_session_app.task(bind=True, base=Task)
    def add1(self, a, b):
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

    with mock.patch("taskbadger.celery.create_task") as create, mock.patch("taskbadger.celery.update_task") as update:
        result = add1.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called()
    update.assert_called()


def test_celery_task_badger_not_configured(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add2(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task") as create, mock.patch("taskbadger.celery.update_task") as update:
        result = add2.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_not_called()
    update.assert_not_called()


def test_task_direct_call(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add3(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task_id is None
            get_task.assert_not_called()

        return a + b

    celery_session_worker.reload()

    assert add3(2, 1) == 3
    result = add3.apply(args=[2, 3])
    assert result.get(timeout=1, propagate=True) == 5


def test_task_shared_task(celery_session_worker, bind_settings):
    @celery.shared_task(bind=True, base=Task)
    def add4(self, a, b):
        with mock.patch("taskbadger.celery.get_task") as get_task:
            assert self.taskbadger_task is not None
            get_task.assert_called()

        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task") as create, mock.patch("taskbadger.celery.update_task") as update:
        result = add4.delay(2, 2)
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called()
    update.assert_called()
