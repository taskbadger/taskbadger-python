from unittest import mock

from taskbadger import track
from taskbadger.mug import Badger, Settings


@mock.patch("taskbadger.decorators.create_task_safe")
@mock.patch("taskbadger.decorators._update_safe")
def test_track_decorator(update, create):
    @track
    def test(arg):
        return arg

    assert test("test") == "test"
    assert create.call_count == 1
    assert (
        create.call_args.args[0]
        == "tests.test_decorators.test_track_decorator.<locals>.test"
    )
    assert update.call_count == 1
    assert update.call_args.kwargs["status"] == "success"


@mock.patch("taskbadger.decorators.create_task_safe")
def test_track_decorator_args(create):
    @track(name="new name", monitor_id="test", max_runtime=1)
    def test(arg):
        return arg

    assert test("test") == "test"
    assert create.call_count == 1
    assert create.call_args.args[0] == "new name"
    assert create.call_args.kwargs["monitor_id"] == "test"
    assert create.call_args.kwargs["max_runtime"] == 1


@mock.patch("taskbadger.decorators.create_task_safe")
@mock.patch("taskbadger.decorators._update_safe")
def test_track_decorator_error(update, create):
    @track
    def test(arg):
        raise Exception("test")

    try:
        test("test")
    except Exception:
        pass
    assert create.call_count == 1
    assert update.call_count == 1
    assert update.call_args.kwargs["status"] == "error"
    assert update.call_args.kwargs["data"]["exception"] == "test"


@mock.patch("taskbadger.decorators._update_safe")
def test_track_decorator_badger_not_configured(update):
    @track
    def test(arg):
        return arg

    assert test("test") == "test"
    assert update.call_count == 0


def test_decorator_session():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))

    @track
    def test(arg):
        return arg

    calls = []

    def _update(*args, **kwargs):
        session = Badger.current.session()
        assert session.client is not None, "Session is not set"
        calls.append("_update")
        return mock.Mock()

    def _create(*args, **kwargs):
        session = Badger.current.session()
        assert session.client is not None, "Session is not set"
        calls.append("_create")
        return mock.Mock()

    with (
        mock.patch("taskbadger.decorators.create_task_safe", new=_create),
        mock.patch("taskbadger.decorators._update_safe", new=_update),
    ):
        assert test("test") == "test"

    assert calls == ["_create", "_update"]
