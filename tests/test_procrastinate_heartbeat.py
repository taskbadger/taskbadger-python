"""Tests for the automatic heartbeat that keeps running Procrastinate tasks fresh."""

import asyncio
from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

from taskbadger import StatusEnum
from taskbadger.exceptions import ConfigurationError
from taskbadger.procrastinate import TB_TASK_ID_KWARG, _instrument_task, track
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration
from tests.utils import task_for_test


@pytest.fixture
def app():
    in_memory = testing.InMemoryConnector()
    app = procrastinate.App(connector=in_memory)
    with app.open():
        yield app


@pytest.fixture
def heartbeat():
    with mock.patch("taskbadger.procrastinate.heartbeat") as heartbeat:
        yield heartbeat


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_runs_for_the_duration_of_the_task(app, heartbeat):
    @track(heartbeat_interval=30)
    @app.task(name="slow")
    def slow():
        heartbeat.start.assert_called_once_with("tb-1", 30)
        heartbeat.stop.assert_not_called()

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
    ):
        slow.func(**{TB_TASK_ID_KWARG: "tb-1"})

    heartbeat.stop.assert_called_once_with("tb-1")


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_stops_when_the_task_fails(app, heartbeat):
    @track(heartbeat_interval=30)
    @app.task(name="slow_boom")
    def slow_boom():
        raise ValueError("nope")

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
        pytest.raises(ValueError, match="nope"),
    ):
        slow_boom.func(**{TB_TASK_ID_KWARG: "tb-2"})

    heartbeat.start.assert_called_once_with("tb-2", 30)
    heartbeat.stop.assert_called_once_with("tb-2")


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_runs_for_async_tasks(app, heartbeat):
    @track(heartbeat_interval=15)
    @app.task(name="slow_async")
    async def slow_async():
        return "done"

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
    ):
        assert asyncio.run(slow_async.func(**{TB_TASK_ID_KWARG: "tb-3"})) == "done"

    heartbeat.start.assert_called_once_with("tb-3", 15)
    heartbeat.stop.assert_called_once_with("tb-3")


@pytest.mark.usefixtures("_bind_settings")
def test_no_heartbeat_by_default(app, heartbeat):
    @app.task(name="plain")
    def plain():
        return 1

    _instrument_task(plain, system=None, manual=True)

    with (
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
    ):
        plain.func(**{TB_TASK_ID_KWARG: "tb-4"})

    heartbeat.start.assert_called_once_with("tb-4", None)


@pytest.mark.usefixtures("_bind_settings")
def test_defer_derives_stale_timeout_from_the_interval(app):
    @track(heartbeat_interval=30)
    @app.task(name="deferred")
    def deferred(a):
        return a

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=task_for_test()) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
    ):
        deferred.defer(a=1)

    assert create.call_args.kwargs["stale_timeout"] == 60


@pytest.mark.usefixtures("_bind_settings")
def test_defer_uses_explicit_stale_timeout(app):
    @track(heartbeat_interval=30, stale_timeout=120)
    @app.task(name="deferred_explicit")
    def deferred_explicit(a):
        return a

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=task_for_test()) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
    ):
        deferred_explicit.defer(a=1)

    assert create.call_args.kwargs["stale_timeout"] == 120


@pytest.mark.usefixtures("_bind_settings")
def test_system_integration_heartbeat(app, heartbeat):
    @app.task(name="auto_heartbeat")
    def auto_heartbeat(a):
        return a

    ProcrastinateSystemIntegration(app=app, heartbeat_interval=45)

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=task_for_test(id="tb-5")) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
    ):
        auto_heartbeat.defer(a=1)
        auto_heartbeat.func(a=1, **{TB_TASK_ID_KWARG: "tb-5"})

    assert create.call_args.kwargs["stale_timeout"] == 90
    heartbeat.start.assert_called_once_with("tb-5", 45)
    heartbeat.stop.assert_called_once_with("tb-5")


@pytest.mark.usefixtures("_bind_settings")
def test_system_integration_heartbeat_for_tracked_task(app, heartbeat):
    """A ``@track``ed task still inherits the system's options when the
    integration is constructed after the task was registered."""

    @track()
    @app.task(name="tracked_auto_heartbeat")
    def tracked_auto_heartbeat(a):
        return a

    ProcrastinateSystemIntegration(app=app, heartbeat_interval=45)

    with (
        mock.patch("taskbadger.procrastinate.create_task_safe", return_value=task_for_test(id="tb-6")) as create,
        mock.patch("taskbadger.procrastinate.update_task_safe"),
        mock.patch("taskbadger.sdk.get_task", return_value=task_for_test(status=StatusEnum.PROCESSING)),
    ):
        tracked_auto_heartbeat.defer(a=1)
        tracked_auto_heartbeat.func(a=1, **{TB_TASK_ID_KWARG: "tb-6"})

    assert create.call_args.kwargs["stale_timeout"] == 90
    heartbeat.start.assert_called_once_with("tb-6", 45)


def test_track_rejects_bad_interval(app):
    with pytest.raises(ConfigurationError):
        track(heartbeat_interval=0)


def test_system_integration_rejects_bad_interval(app):
    with pytest.raises(ConfigurationError):
        ProcrastinateSystemIntegration(app=app, heartbeat_interval=-5)
