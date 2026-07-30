"""Integration tests for the Procrastinate integration.

Requires a running Postgres instance reachable via the ``PROCRASTINATE_DSN``
env var (e.g. ``postgresql://postgres:postgres@localhost:5432/procrastinate``)
and valid TaskBadger creds in ``TASKBADGER_*``.

These tests are excluded from the default pytest run via ``norecursedirs`` in
pyproject.toml.
"""

import datetime
import logging
import os
import random
import time

import procrastinate
import psycopg
import pytest

import taskbadger
from taskbadger import StatusEnum
from taskbadger.procrastinate import current_task, track
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration

PROCRASTINATE_DSN = os.environ.get(
    "PROCRASTINATE_DSN",
    "postgresql://postgres:postgres@localhost:5432/procrastinate",
)

HEARTBEAT_INTERVAL = 1
# long enough for the heartbeat to fire while the task is still running
SLOW_TASK_DURATION = 3


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    for when in ("call", "setup", "teardown"):
        errors = [r.getMessage() for r in caplog.get_records(when) if r.levelno == logging.ERROR]
        if errors:
            pytest.fail(f"log errors during '{when}': {errors}")


@pytest.fixture(scope="session")
def _schema():
    # apply_schema is NOT idempotent (schema.sql uses bare CREATE TYPE), so
    # only apply when the schema isn't already present.
    with psycopg.connect(PROCRASTINATE_DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('procrastinate_jobs')")
        if cur.fetchone()[0] is not None:
            return
    schema_conn = procrastinate.SyncPsycopgConnector(conninfo=PROCRASTINATE_DSN)
    schema_app = procrastinate.App(connector=schema_conn)
    with schema_app.open():
        schema_app.schema_manager.apply_schema()


@pytest.fixture
def app(_schema):
    # Async connector: run_worker raises SyncConnectorConfigurationError on
    # SyncPsycopgConnector. Async connectors work in sync contexts too.
    #
    # Function-scoped because run_worker tears down the sync sub-connector that
    # PsycopgConnector spawns inside `app.open()`, leaving the next test's
    # defer() with no usable sync pool.
    conn = procrastinate.PsycopgConnector(conninfo=PROCRASTINATE_DSN)
    app = procrastinate.App(connector=conn)
    with app.open():
        yield app


def _fetch_job_args(job_id):
    # Direct sync psycopg connection — the app's pool is async (see fixture).
    with psycopg.connect(PROCRASTINATE_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT args FROM procrastinate_jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
    return row[0]


def test_track_decorator(app):
    @track
    @app.task(name="add_manual", queue="taskbadger_int")
    def add_manual(a, b):
        tb = current_task()
        assert tb is not None
        tb.update(value=100, data={"result": a + b})
        return a + b

    a, b = random.randint(1, 1000), random.randint(1, 1000)
    job_id = add_manual.defer(a=a, b=b)
    app.run_worker(
        queues=["taskbadger_int"],
        wait=False,
        install_signal_handlers=False,
        listen_notify=False,
    )

    # The TB task id was stashed in the job kwargs at defer time. Read it back
    # from Procrastinate to verify the final state.
    args = _fetch_job_args(job_id)
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
    assert fetched.value == 100
    assert fetched.data == {"result": a + b}


def test_heartbeat(app):
    """The worker pings the task while it runs, so it doesn't go stale."""

    @track(heartbeat_interval=HEARTBEAT_INTERVAL)
    @app.task(name="slow", queue="taskbadger_int_hb")
    def slow():
        # `run_worker` blocks the test, so sample the task's `updated` time from
        # inside the body. Fetched directly to bypass the integration's cache.
        tb_id = current_task().id
        before = taskbadger.get_task(tb_id).updated
        time.sleep(SLOW_TASK_DURATION)
        after = taskbadger.get_task(tb_id).updated
        current_task().update(data={"before": before.isoformat(), "after": after.isoformat()})

    job_id = slow.defer()
    app.run_worker(
        queues=["taskbadger_int_hb"],
        wait=False,
        install_signal_handlers=False,
        listen_notify=False,
    )

    args = _fetch_job_args(job_id)
    fetched = taskbadger.get_task(args["__taskbadger_task_id__"])

    assert fetched.status == StatusEnum.SUCCESS
    assert fetched.stale_timeout == HEARTBEAT_INTERVAL * 2
    before = datetime.datetime.fromisoformat(fetched.data["before"])
    after = datetime.datetime.fromisoformat(fetched.data["after"])
    assert after > before, "task was not pinged while it was running"


def test_auto_track_via_system(app):
    ProcrastinateSystemIntegration(app=app, auto_track_tasks=True)

    @app.task(name="add_auto", queue="taskbadger_int_auto")
    def add_auto(a, b):
        return a + b

    a, b = random.randint(1, 1000), random.randint(1, 1000)
    job_id = add_auto.defer(a=a, b=b)
    app.run_worker(
        queues=["taskbadger_int_auto"],
        wait=False,
        install_signal_handlers=False,
        listen_notify=False,
    )

    args = _fetch_job_args(job_id)
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
