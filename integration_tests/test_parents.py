import pytest

import taskbadger as badger
from taskbadger.exceptions import UnexpectedStatus


def test_create_child_task():
    parent = badger.create_task("test parent")
    child = badger.create_task("test child", parent=parent.id)

    assert child.parent == parent.id
    assert badger.get_task(child.id).parent == parent.id
    # the parent itself stays a root
    assert not badger.get_task(parent.id).parent


def test_list_tasks_by_parent():
    parent = badger.create_task("test parent for listing")
    child = badger.create_task("test child for listing", parent=parent.id)
    badger.create_task("test unrelated task")

    children = badger.list_tasks(parent=parent.id).results

    assert [task.id for task in children] == [child.id]


def test_set_parent_on_an_existing_task():
    parent = badger.create_task("test parent for update")
    child = badger.create_task("test child for update")
    assert not child.parent

    child.update(parent=parent.id)

    assert child.parent == parent.id
    assert badger.get_task(child.id).parent == parent.id


def test_nesting_is_limited_to_one_level():
    """The API rejects a grandchild, which is what the integrations' flattening
    exists to avoid."""
    parent = badger.create_task("test parent depth")
    child = badger.create_task("test child depth", parent=parent.id)

    with pytest.raises(UnexpectedStatus):
        badger.create_task("test grandchild depth", parent=child.id)
