import asyncio
import logging
from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

from taskbadger import StatusEnum
from taskbadger.procrastinate import TB_TASK_ID_KWARG, _instrument_task
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    errors = [r.getMessage() for r in caplog.get_records("call") if r.levelno == logging.ERROR]
    if errors:
        pytest.fail(f"log errors during tests: {errors}")


@pytest.fixture
def app():
    in_memory = testing.InMemoryConnector()
    app = procrastinate.App(connector=in_memory)
    with app.open():
        yield app


@pytest.mark.usefixtures("_bind_settings")
def test_worker_updates_task_sync(app):
    @app.task(name="add")
    def add(a, b):
        return a + b

    _instrument_task(add, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING)
        add.func(a=2, b=3, **{TB_TASK_ID_KWARG: "tb-123"})

    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]
    # The reserved key must not appear in the calls (it's stripped before user fn)
    assert all(TB_TASK_ID_KWARG not in c.kwargs for c in update.call_args_list)


@pytest.mark.usefixtures("_bind_settings")
def test_worker_updates_task_async(app):
    @app.task(name="add_async")
    async def add_async(a, b):
        return a + b

    _instrument_task(add_async, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING)
        result = asyncio.run(add_async.func(a=2, b=3, **{TB_TASK_ID_KWARG: "tb-456"}))

    assert result == 5
    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]


@pytest.mark.usefixtures("_bind_settings")
def test_worker_marks_error(app):
    @app.task(name="boom")
    def boom():
        raise ValueError("nope")

    _instrument_task(boom, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(status=StatusEnum.PROCESSING, data={"x": 1})
        update.return_value = task_for_test(status=StatusEnum.PROCESSING, data={"x": 1})
        with pytest.raises(ValueError, match="nope"):
            boom.func(**{TB_TASK_ID_KWARG: "tb-789"})

    statuses = [call.kwargs["status"] for call in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.ERROR]
    err_call = update.call_args_list[-1]
    assert err_call.kwargs["data"] == {"x": 1, "exception": "nope"}


@pytest.mark.usefixtures("_bind_settings")
def test_worker_no_id_runs_clean(app):
    @app.task(name="add2")
    def add2(a, b):
        return a + b

    _instrument_task(add2, system=None, manual=True)

    with mock.patch("taskbadger.procrastinate.update_task_safe") as update:
        result = add2.func(a=1, b=2)

    assert result == 3
    update.assert_not_called()


@pytest.mark.usefixtures("_bind_settings")
def test_defer_creates_pending_task_and_injects_id(app):
    @app.task(name="add3")
    def add3(a, b):
        return a + b

    _instrument_task(add3, system=None, manual=True)

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        add3.defer(a=1, b=2)

    create.assert_called_once()
    assert create.call_args.args == ("add3",)
    assert create.call_args.kwargs == {"status": StatusEnum.PENDING}

    # The injected id should appear in the Procrastinate job's task kwargs.
    jobs = list(app.connector.jobs.values())
    assert len(jobs) == 1
    assert jobs[0]["args"][TB_TASK_ID_KWARG] == tb.id


def test_defer_no_taskbadger_when_unconfigured(app):
    @app.task(name="add4")
    def add4(a, b):
        return a + b

    _instrument_task(add4, system=None, manual=True)

    # Badger is not configured (no _bind_settings fixture).
    with mock.patch("taskbadger.procrastinate.create_task_safe") as create:
        add4.defer(a=1, b=2)

    create.assert_not_called()
    jobs = list(app.connector.jobs.values())
    assert TB_TASK_ID_KWARG not in jobs[0]["args"]


@pytest.mark.usefixtures("_bind_settings")
def test_defer_async_injects_id(app):
    @app.task(name="add5")
    async def add5(a, b):
        return a + b

    _instrument_task(add5, system=None, manual=True)

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb):
        asyncio.run(add5.defer_async(a=1, b=2))

    jobs = list(app.connector.jobs.values())
    assert jobs[0]["args"][TB_TASK_ID_KWARG] == tb.id


@pytest.mark.usefixtures("_bind_settings")
def test_end_to_end_via_worker(app):
    @app.task(name="add6")
    def add6(a, b):
        return a + b

    _instrument_task(add6, system=None, manual=True)

    tb = task_for_test()
    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe") as update,
        mock.patch("taskbadger.procrastinate.get_task") as get,
    ):
        get.return_value = task_for_test(id=tb.id, status=StatusEnum.PROCESSING)
        add6.defer(a=2, b=3)
        app.run_worker(wait=False, install_signal_handlers=False, listen_notify=False)

    create.assert_called_once()
    statuses = [c.kwargs["status"] for c in update.call_args_list]
    assert statuses == [StatusEnum.PROCESSING, StatusEnum.SUCCESS]
