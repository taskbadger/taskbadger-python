import asyncio
from unittest import mock

import procrastinate
import pytest
from procrastinate import testing

from taskbadger.procrastinate import _INSTRUMENTED_ATTR, TB_TASK_ID_KWARG, track
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration
from tests.utils import task_for_test


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


@pytest.mark.usefixtures("_bind_settings")
def test_wraps_tasks_registered_after_init(app):
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    @app.task(name="late")
    def late(a):
        return a

    assert getattr(late, _INSTRUMENTED_ATTR) is True

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        late.defer(a=1)

    create.assert_called_once()


@pytest.mark.usefixtures("_bind_settings")
def test_periodic_defer_creates_pending(app):
    """Periodic tasks are deferred via ``app.job_manager.defer_periodic_job``,
    which bypasses ``task.defer``/``defer_async`` entirely. The system
    integration must hook this path too, otherwise periodic jobs are invisible
    to TaskBadger."""

    @app.task(name="periodic_target")
    def periodic_target(timestamp):
        return timestamp

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    timestamp = 1700000000
    job = periodic_target.configure(task_kwargs={"timestamp": timestamp}).job

    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        asyncio.run(app.job_manager.defer_periodic_job(job=job, periodic_id="every-min", defer_timestamp=timestamp))

    create.assert_called_once()
    jobs_stored = list(app.connector.jobs.values())
    assert jobs_stored[0]["args"][TB_TASK_ID_KWARG] == tb.id


@pytest.mark.usefixtures("_bind_settings")
def test_periodic_defer_skips_excluded(app):
    """Excludes apply on the periodic path too."""

    @app.task(name="myapp.cleanup.flush")
    def flush(timestamp):
        pass

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True, excludes=[r"myapp\.cleanup\..*"])

    timestamp = 1700000000
    job = flush.configure(task_kwargs={"timestamp": timestamp}).job

    with mock.patch("taskbadger.procrastinate.create_task_safe") as create:
        asyncio.run(app.job_manager.defer_periodic_job(job=job, periodic_id="every-min", defer_timestamp=timestamp))

    create.assert_not_called()


@pytest.mark.usefixtures("_bind_settings")
def test_track_plus_auto_track_no_double_wrap(app):
    @track
    @app.task(name="manual_plus_auto")
    def both():
        pass

    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    # _instrument_task is idempotent — system init must not re-wrap.
    tb = task_for_test()
    with mock.patch("taskbadger.procrastinate.create_task_safe", return_value=tb) as create:
        both.defer()

    assert create.call_count == 1
    jobs = list(app.connector.jobs.values())
    args = jobs[0]["args"]
    assert list(args).count(TB_TASK_ID_KWARG) == 1
