"""
Note
====

As part of the Celery fixture setup a 'ping' task is run which executes
before the `bind_settings` fixture is executed. This means that if any code
calls `Badger.is_configured()` (or similar), the `_local` ContextVar in the
Celery runner thread will not have the configuration set.
"""

import logging
import sys
import weakref
from unittest import mock

import pytest
from celery.signals import task_prerun

from taskbadger.mug import Badger, Settings
from taskbadger.systems.celery import CelerySystemIntegration
from tests.utils import task_for_test


@pytest.fixture()
def _bind_settings_with_system():
    systems = [CelerySystemIntegration()]
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


@pytest.mark.usefixtures(_bind_settings_with_system)
def test_celery_auto_track_task(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True)
    def add_normal(self, a, b):
        assert self.request.get("taskbadger_task_id") is not None, "missing task in request"
        assert not hasattr(self, "taskbadger_task")
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
        assert result.get(timeout=10, propagate=True) == 4

    create.assert_called_once()
    assert get_task.call_count == 1
    assert update.call_count == 2
    assert Badger.current.session().client is None


@pytest.mark.parametrize(
    ("include", "exclude", "expected"),
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


def test_celery_system_integration_connects_signals():
    # clean the slate
    _disconnect_signals()
    if "taskbadger.celery" in sys.modules:
        del sys.modules["taskbadger.celery"]
    assert "taskbadger.celery" not in sys.modules

    # this should result in the signals being connected
    CelerySystemIntegration()

    assert "taskbadger.celery" in sys.modules
    _assert_signals()


def _assert_signals(check_is_connected=True):
    # test that signals are actually connected
    receivers = [rcv[1] for rcv in task_prerun.receivers]
    receiver_names = set()
    for receiver in receivers:
        if isinstance(receiver, weakref.ReferenceType):
            receiver = receiver()
        receiver_names.add(f"{receiver.__module__}.{receiver.__name__}")
    is_connected = "taskbadger.celery.task_prerun_handler" in receiver_names
    assert check_is_connected == is_connected


def _disconnect_signals():
    from taskbadger.celery import task_prerun_handler

    task_prerun.disconnect(task_prerun_handler)
    _assert_signals(check_is_connected=False)
