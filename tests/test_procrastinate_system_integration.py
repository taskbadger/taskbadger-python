from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

from taskbadger.procrastinate import _INSTRUMENTED_ATTR, TB_TASK_ID_KWARG, _task_cache
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration
from tests.utils import task_for_test


@pytest.fixture(autouse=True)
def _clear_task_cache():
    _task_cache.cache.clear()
    yield
    _task_cache.cache.clear()


@pytest.fixture
def app():
    in_memory = testing.InMemoryConnector()
    app = procrastinate.App(connector=in_memory)
    with app.open():
        yield app


@pytest.mark.parametrize(
    ("include", "exclude", "expected"),
    [
        (None, None, True),
        (["myapp.tasks.export_data"], None, True),
        ([".*export_data"], [], True),
        ([".*export_da"], [], False),
        (["myapp.tasks.export_data"], ["myapp.tasks.export_data"], False),
        ([".*"], ["myapp.tasks.export_data"], False),
        ([".*"], [".*tasks.*"], False),
    ],
)
def test_task_name_matching(app, include, exclude, expected):
    integration = ProcrastinateSystemIntegration(app=app, includes=include, excludes=exclude)
    assert integration.track_task("myapp.tasks.export_data") is expected


def test_auto_track_off_returns_false(app):
    integration = ProcrastinateSystemIntegration(app=app, auto_track_tasks=False)
    assert integration.track_task("anything") is False


def test_wraps_existing_tasks(app):
    @app.task(name="pre_existing")
    def pre_existing(a):
        return a

    assert not getattr(pre_existing, _INSTRUMENTED_ATTR, False)
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)
    assert getattr(pre_existing, _INSTRUMENTED_ATTR) is True


@pytest.mark.usefixtures("_bind_settings")
def test_auto_track_creates_pending(app):
    @app.task(name="auto_target")
    def auto_target(a):
        return a

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        auto_target.defer(a=1)

    create.assert_called_once()
    # InMemoryConnector.jobs is a dict keyed by int; kwargs under "args"
    jobs = list(app.connector.jobs.values())
    assert jobs[0]["args"][TB_TASK_ID_KWARG] == tb.id


@pytest.mark.usefixtures("_bind_settings")
def test_auto_track_excludes_skip(app):
    @app.task(name="myapp.cleanup.flush")
    def flush():
        pass

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True, excludes=[r"myapp\.cleanup\..*"])

    with mock.patch("taskbadger.procrastinate.create_task_safe") as create:
        flush.defer()

    create.assert_not_called()
