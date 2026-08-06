import logging
import random
import time

import pytest
from celery import chain

import taskbadger
from taskbadger import StatusEnum

from .tasks import HEARTBEAT_INTERVAL, add, add_auto_track, chain_head, chain_tail, slow_add, spawns_child


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


def test_celery_child_task_nests_under_its_parent(celery_session_app, celery_session_worker):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    root = spawns_child.delay(a, b)
    child_celery_id = root.get(timeout=15, propagate=True)

    child = celery_session_app.AsyncResult(child_celery_id).get(timeout=15, propagate=True)

    assert taskbadger.get_task(child["own_tb_id"]).parent == root.taskbadger_task_id


def test_celery_grandchild_is_flattened_onto_the_root(celery_session_app, celery_session_worker):
    """Nesting stops at one level, so a task deferred by a child joins it under
    the root instead of hanging off it (which the API would reject)."""
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    root = spawns_child.delay(a, b)
    child_celery_id = root.get(timeout=15, propagate=True)

    child = celery_session_app.AsyncResult(child_celery_id).get(timeout=15, propagate=True)
    grandchild = taskbadger.get_task(child["grandchild_tb_id"])

    assert grandchild.parent == root.taskbadger_task_id
    assert grandchild.parent != child["own_tb_id"]


def test_celery_chain_links_are_not_nested(celery_session_app, celery_session_worker):
    """Celery dispatches the next chain link from inside the previous task's run,
    so it would otherwise be nested under it. Links are successors, not subtasks.
    """
    ids = chain(chain_head.s(), chain_tail.s()).apply_async().get(timeout=20, propagate=True)

    assert ids["head_tb_id"], "the first link should be tracked"
    assert ids["own_tb_id"], "the second link should be tracked"
    assert not taskbadger.get_task(ids["own_tb_id"]).parent
    assert taskbadger.list_tasks(parent=ids["head_tb_id"]).results == []


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
