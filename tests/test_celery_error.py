from unittest import mock

import pytest

from taskbadger import StatusEnum
from taskbadger.celery import Task
from taskbadger.mug import Badger
from tests.utils import task_for_test


def test_celery_task_error(celery_session_app, celery_session_worker, bind_settings):
    @celery_session_app.task(bind=True, base=Task)
    def add_error(self, a, b):
        assert self.taskbadger_task is not None
        assert Badger.current.session().client is not None
        raise Exception("error")

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update, mock.patch("taskbadger.celery.get_task") as get_task:
        get_task.return_value = task_for_test()
        result = add_error.delay(2, 2)
        with pytest.raises(Exception):
            result.get(timeout=10, propagate=True)

    create.assert_called()
    update.assert_has_calls(
        [
            mock.call(mock.ANY, status=StatusEnum.PROCESSING, data=mock.ANY),
            mock.call(mock.ANY, status=StatusEnum.ERROR, data=mock.ANY),
        ]
    )
    data_kwarg = update.call_args_list[1][1]["data"]
    assert "Traceback" in data_kwarg["exception"]
    assert Badger.current.session().client is None
