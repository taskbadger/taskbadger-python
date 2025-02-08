import pytest

from taskbadger import create_task, init
from taskbadger.mug import GLOBAL_MUG, Badger
from tests.test_sdk_primatives import _json_task_response, _verify_task


def test_scope_singleton():
    assert Badger.current == GLOBAL_MUG
    scope = Badger.current.scope()
    assert scope.context == {}
    assert scope.stack == []
    assert scope == Badger.current.scope()


def test_scope_context():
    scope = Badger.current.scope()
    assert scope.context == {}
    assert scope.stack == []
    with scope:
        assert scope.stack == [{}]
        scope.context["foo"] = "bar"
        with scope:
            assert scope.stack == [{}, {"foo": "bar"}]
            assert scope.context == {"foo": "bar"}
            scope.context["bar"] = "bazz"
            with scope:
                assert scope.context == {"foo": "bar", "bar": "bazz"}
                scope.context.clear()
        assert scope.context == {"foo": "bar"}
        assert scope.stack == [{}]
    assert scope.context == {}
    assert scope.stack == []


@pytest.fixture(autouse=True)
def init_skd():
    init("org", "project", "token")


def test_create_task_with_scope(httpx_mock):
    with Badger.current.scope() as scope:
        scope["foo"] = "bar"
        scope["bar"] = "bazz"
        httpx_mock.add_response(
            url="https://taskbadger.net/api/org/project/tasks/",
            method="POST",
            match_headers={"Authorization": "Bearer token"},
            match_content=b'{"name": "name", "status": "pending", "data": {"foo": "bar", "bar": "buzzer"}}',
            json=_json_task_response(),
            status_code=201,
        )
        task = create_task("name", data={"bar": "buzzer"})
        _verify_task(task)
