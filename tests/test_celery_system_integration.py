"""
Note
====

As part of the Celery fixture setup a 'ping' task is run which executes
before the `bind_settings` fixture is executed. This means that if any code
calls `Badger.is_configured()` (or similar), the `_local` ContextVar in the
Celery runner thread will not have the configuration set.
"""
import logging
from unittest import mock

import pytest

from taskbadger.mug import Badger, Settings
from taskbadger.systems.celery import CelerySystemIntegration
from tests.utils import task_for_test


@pytest.fixture
def bind_settings_with_system():
    systems = [CelerySystemIntegration()]
    Badger.current.bind(
        Settings(
            "https://taskbadger.net", "token", "org", "proj", systems={system.identifier: system for system in systems}
        )
    )
    yield
    Badger.current.bind(None)


@pytest.fixture(autouse=True)
def check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


def test_celery_auto_track_task(celery_session_app, celery_session_worker, bind_settings_with_system):
    @celery_session_app.task(bind=True)
    def add_normal(self, a, b):
        assert self.request.get("taskbadger_task_id") is not None, "missing task in request"
        assert not hasattr(self, "taskbadger_task")
        assert Badger.current.session().client is not None, "missing client"
        return a + b

    celery_session_worker.reload()

    with mock.patch("taskbadger.celery.create_task_safe") as create, mock.patch(
        "taskbadger.celery.update_task_safe"
    ) as update, mock.patch("taskbadger.celery.get_task") as get_task:
        tb_task = task_for_test()
        create.return_value = tb_task
        result = add_normal.delay(2, 2)
        assert result.info.get("taskbadger_task_id") == tb_task.id
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once()
    assert get_task.call_count == 1
    assert update.call_count == 2
    assert Badger.current.session().client is None


@pytest.mark.parametrize(
    "include,exclude,expected",
    [
        (None, None, True),
        (["myapp.tasks.export_data"], None, True),
        ([".*export_data"], [], True),
        ([".*export_da"], [], False),
        (["myapp.tasks.export_data"], ["myapp.tasks.export_data"], False),
        ([".*"], ["myapp.tasks.export_data"], False),
        ([".*"], [".*tasks.*"], False),
    ],
)
def test_task_name_matching(include, exclude, expected: bool):
    integration = CelerySystemIntegration(includes=include, excludes=exclude)
    assert integration.track_task("myapp.tasks.export_data") is expected
