import logging
import random
import time

import pytest

import taskbadger
from taskbadger import StatusEnum

from .tasks import HEARTBEAT_INTERVAL, add, add_auto_track, slow_add


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    for when in ("call", "setup", "teardown"):
        errors = [r.getMessage() for r in caplog.get_records(when) if r.levelno == logging.ERROR]
        if errors:
            pytest.fail(f"log errors during '{when}': {errors}")


@pytest.fixture(scope="session", autouse=True)
def celery_includes():
    return [
        "integration_tests.tasks",
    ]


def test_celery(celery_session_app, celery_session_worker):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = add.delay(a, b)
    assert result.get(timeout=10, propagate=True) == a + b

    tb_task = result.get_taskbadger_task()
    assert tb_task is not None
    assert tb_task.status == StatusEnum.SUCCESS
    assert tb_task.value == 100
    assert tb_task.data == {"result": a + b}
    assert tb_task.tags == {"env": "integration"}


def test_celery_auto_track(celery_session_app, celery_session_worker):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = add_auto_track.delay(a, b)
    assert result.get(timeout=10, propagate=True) == a + b


def test_celery_heartbeat(celery_session_app, celery_session_worker):
    """The worker pings the task while it runs, so it doesn't go stale."""
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = slow_add.delay(a, b)

    running = _wait_for_status(result.taskbadger_task_id, StatusEnum.PROCESSING)
    assert running.stale_timeout == HEARTBEAT_INTERVAL * 2

    time.sleep(HEARTBEAT_INTERVAL * 2)
    pinged = taskbadger.get_task(running.id)

    assert result.get(timeout=30, propagate=True) == a + b
    # still running, so the task can only have been touched by the heartbeat
    assert pinged.status == StatusEnum.PROCESSING
    assert pinged.updated > running.updated, "task was not pinged while it was running"


def _wait_for_status(task_id, status, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = taskbadger.get_task(task_id)
        if task.status == status:
            return task
        time.sleep(0.2)
    pytest.fail(f"task '{task_id}' did not reach status '{status}'")
