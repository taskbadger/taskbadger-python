import logging
import random

import pytest
from pytest_celery import CeleryBackendCluster, CeleryBrokerCluster, RedisTestBackend, RedisTestBroker

from taskbadger import StatusEnum

from .tasks import add, add_auto_track


@pytest.fixture(autouse=True)
def check_log_errors(caplog):
    yield
    for when in ("call", "setup", "teardown"):
        errors = [r.getMessage() for r in caplog.get_records(when) if r.levelno == logging.ERROR]
        if errors:
            pytest.fail(f"log errors during '{when}': {errors}")


@pytest.fixture
def celery_broker_cluster(celery_redis_broker: RedisTestBroker) -> CeleryBrokerCluster:
    cluster = CeleryBrokerCluster(celery_redis_broker)
    yield cluster
    cluster.teardown()


@pytest.fixture
def celery_backend_cluster(celery_redis_backend: RedisTestBackend) -> CeleryBackendCluster:
    cluster = CeleryBackendCluster(celery_redis_backend)
    yield cluster
    cluster.teardown()


@pytest.fixture
def default_worker_tasks(default_worker_tasks: set) -> set:
    from integration_tests import tasks

    default_worker_tasks.add(tasks)
    return default_worker_tasks


def test_celery(celery_setup):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = add.delay(a, b)
    assert result.get(timeout=10, propagate=True) == a + b

    tb_task = result.get_taskbadger_task()
    assert tb_task is not None
    assert tb_task.status == StatusEnum.SUCCESS
    assert tb_task.value == 100
    assert tb_task.data == {"result": a + b}


def test_celery_auto_track(celery_setup):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = add_auto_track.delay(a, b)
    assert result.get(timeout=10, propagate=True) == a + b
