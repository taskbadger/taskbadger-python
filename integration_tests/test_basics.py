import datetime

import taskbadger as badger
from taskbadger import StatusEnum


def test_basics():
    data = {"now": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    task = badger.create_task("test basics", data=data)
    task.success(100)
    assert task.status == StatusEnum.SUCCESS
    assert task.tags == {"env": "integration"}

    fresh = badger.get_task(task.id)
    assert fresh.status == StatusEnum.SUCCESS
    assert fresh.value == 100
    assert fresh.data == data
    assert fresh.tags == {"env": "integration"}
