import logging
import time
from http import HTTPStatus
from unittest import mock

import pytest

from taskbadger import StatusEnum
from taskbadger._heartbeat import heartbeat
from taskbadger._integrations import resolve_heartbeat_options, validate_interval
from taskbadger.exceptions import ConfigurationError
from taskbadger.internal.types import Response
from taskbadger.mug import Badger
from tests.utils import task_for_test

INTERVAL = 0.05


def _wait_for_call_count(mock_obj, expected, timeout=5.0):
    deadline = time.monotonic() + timeout
    while mock_obj.call_count < expected and time.monotonic() < deadline:
        time.sleep(0.01)
    return mock_obj.call_count


@pytest.fixture
def update():
    with mock.patch("taskbadger._heartbeat.update_task_safe") as update:
        update.return_value = None
        yield update


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_pings_until_stopped(update):
    heartbeat.start("tb-1", INTERVAL)
    assert _wait_for_call_count(update, 2) >= 2
    update.assert_called_with("tb-1")

    heartbeat.stop("tb-1")
    time.sleep(INTERVAL * 3)
    calls = update.call_count
    time.sleep(INTERVAL * 3)
    assert update.call_count == calls


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_ping_is_an_empty_update():
    """The beat thread has its own context, so it has to build its own client."""
    with mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as request:
        # a terminal status unregisters the task, so only one request is made
        request.return_value = Response(HTTPStatus.OK, b"", {}, task_for_test(status=StatusEnum.SUCCESS))
        heartbeat.start("tb-9", INTERVAL)
        assert _wait_for_call_count(request, 1) == 1
        heartbeat.stop("tb-9")

    assert request.call_args.kwargs["id"] == "tb-9"
    assert request.call_args.kwargs["body"].to_dict() == {}


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_stops_when_task_reaches_terminal_state(update):
    update.return_value = task_for_test(status=StatusEnum.SUCCESS)

    heartbeat.start("tb-2", INTERVAL)
    assert _wait_for_call_count(update, 1) == 1

    time.sleep(INTERVAL * 3)
    assert update.call_count == 1


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_binds_settings_in_the_beat_thread(update):
    seen = []
    update.side_effect = lambda task_id: seen.append(Badger.current.settings)

    heartbeat.start("tb-3", INTERVAL)
    _wait_for_call_count(update, 1)
    heartbeat.stop("tb-3")

    assert seen[0] is Badger.current.settings


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_pings_multiple_tasks(update):
    heartbeat.start("tb-4", INTERVAL)
    heartbeat.start("tb-5", INTERVAL)
    _wait_for_call_count(update, 4)
    heartbeat.stop("tb-4")
    heartbeat.stop("tb-5")

    task_ids = {call.args[0] for call in update.call_args_list}
    assert task_ids == {"tb-4", "tb-5"}


@pytest.mark.usefixtures("_bind_settings")
@pytest.mark.parametrize("interval", [None, 0, -1])
def test_heartbeat_ignores_missing_interval(update, interval):
    heartbeat.start("tb-6", interval)
    time.sleep(INTERVAL * 3)
    update.assert_not_called()


def test_heartbeat_ignores_unconfigured_client(update):
    heartbeat.start("tb-7", INTERVAL)
    time.sleep(INTERVAL * 3)
    update.assert_not_called()


@pytest.mark.parametrize("interval", [0, -1, "30"])
def test_validate_interval_rejects_bad_values(interval):
    with pytest.raises(ConfigurationError):
        validate_interval(interval)


class FakeSystem:
    def __init__(self, heartbeat_interval=None, stale_timeout=None):
        self.heartbeat_interval = heartbeat_interval
        self.stale_timeout = stale_timeout


@pytest.mark.parametrize(
    ("interval", "stale_timeout", "system", "expected"),
    [
        (None, None, None, (None, None)),
        (None, None, FakeSystem(), (None, None)),
        # a stale timeout is derived from the interval
        (30, None, None, (30, 60)),
        (None, None, FakeSystem(heartbeat_interval=30), (30, 60)),
        # an explicit stale timeout wins over the derived one
        (30, 45, None, (30, 45)),
        (30, None, FakeSystem(stale_timeout=45), (30, 45)),
        # task options win over the system integration
        (10, None, FakeSystem(heartbeat_interval=30), (10, 20)),
        (None, 45, FakeSystem(heartbeat_interval=30, stale_timeout=90), (30, 45)),
        # a stale timeout on its own doesn't imply a heartbeat
        (None, 45, None, (None, 45)),
    ],
)
def test_resolve_heartbeat_options(interval, stale_timeout, system, expected):
    assert resolve_heartbeat_options(interval, stale_timeout, system) == expected


@pytest.mark.usefixtures("_bind_settings")
def test_heartbeat_ignores_invalid_interval(update):
    heartbeat.start("tb-8", "30")
    time.sleep(INTERVAL * 3)
    update.assert_not_called()


def test_resolve_heartbeat_options_ignores_invalid_interval(caplog):
    with caplog.at_level(logging.WARNING, logger="taskbadger"):
        assert resolve_heartbeat_options("30", None, None) == (None, None)
    assert "Ignoring invalid heartbeat_interval" in caplog.text
