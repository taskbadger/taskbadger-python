import pytest

from taskbadger import create_task, init
from taskbadger.mug import GLOBAL_MUG, Badger
from tests.test_sdk_primatives import _json_task_response, _verify_task


def test_scope_singleton():
    assert Badger.current == GLOBAL_MUG
    scope = Badger.current.scope()
    assert scope.context == {}
    assert scope.tags == {}
    assert scope.stack == []
    assert scope == Badger.current.scope()


def test_scope_context():
    scope = Badger.current.scope()
    assert scope.context == {}
    assert scope.tags == {}
    assert scope.stack == []
    with scope:
        assert scope.stack == [({}, {})]
        scope.context["foo"] = "bar"
        scope.tags["name"] = "value"
        with scope:
            assert scope.stack == [({}, {}), ({"foo": "bar"}, {"name": "value"})]
            assert scope.context == {"foo": "bar"}
            assert scope.tags == {"name": "value"}
            scope.context["bar"] = "bazz"
            scope.tags["bar"] = "bazz"
            with scope:
                assert scope.context == {"foo": "bar", "bar": "bazz"}
                assert scope.tags == {"name": "value", "bar": "bazz"}
                scope.context.clear()
                scope.tags.clear()
        assert scope.context == {"foo": "bar"}
        assert scope.tags == {"name": "value"}
        assert scope.stack == [({}, {})]
    assert scope.context == {}
    assert scope.tags == {}
    assert scope.stack == []


@pytest.fixture(autouse=True)
def _init_skd():
    init("org", "project", "token")


def test_create_task_with_scope(httpx_mock):
    with Badger.current.scope() as scope:
        scope["foo"] = "bar"
        scope["bar"] = "bazz"
        scope.tag({"name": "value"})
        httpx_mock.add_response(
            url="https://taskbadger.net/api/org/project/tasks/",
            method="POST",
            match_headers={"Authorization": "Bearer token"},
            match_content=b'{"name": "name", "status": "pending", '
            b'"data": {"foo": "bar", "bar": "buzzer"}, '
            b'"tags": {"name": "value", "name1": "value1"}}',
            json=_json_task_response(),
            status_code=201,
        )
        task = create_task("name", data={"bar": "buzzer"}, tags={"name1": "value1"})
        _verify_task(task)
