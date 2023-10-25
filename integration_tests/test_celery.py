import random

import pytest

from taskbadger import StatusEnum

from .tasks import add


@pytest.fixture(scope="session", autouse=True)
def celery_includes():
    return [
        "integration_tests.tasks",
    ]


def test_celery(celery_worker):
    a, b = random.randint(1, 1000), random.randint(1, 1000)
    result = add.delay(a, b)
    assert result.get(timeout=10, propagate=True) == a + b

    tb_task = result.get_taskbadger_task()
    assert tb_task is not None
    assert tb_task.status == StatusEnum.SUCCESS
    assert tb_task.value == 100
    assert tb_task.data == {"result": a + b}
