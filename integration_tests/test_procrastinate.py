"""Integration tests for the Procrastinate integration.

Requires a running Postgres instance reachable via the ``PROCRASTINATE_DSN``
env var (e.g. ``postgresql://postgres:postgres@localhost:5432/procrastinate``)
and valid TaskBadger creds in ``TASKBADGER_*``.

These tests are excluded from the default pytest run via ``norecursedirs`` in
pyproject.toml.
"""

import logging
import os
import random

import procrastinate
import pytest

import taskbadger
from taskbadger import StatusEnum
from taskbadger.procrastinate import current_task, track
from taskbadger.systems.procrastinate import ProcrastinateSystemIntegration

PROCRASTINATE_DSN = os.environ.get(
    "PROCRASTINATE_DSN",
    "postgresql://postgres:postgres@localhost:5432/procrastinate",
)


@pytest.fixture(autouse=True)
def _check_log_errors(caplog):
    yield
    for when in ("call", "setup", "teardown"):
        errors = [r.getMessage() for r in caplog.get_records(when) if r.levelno == logging.ERROR]
        if errors:
            pytest.fail(f"log errors during '{when}': {errors}")


@pytest.fixture(scope="session")
def app():
    """A Procrastinate app pointed at a real Postgres instance with its schema applied."""
    conn = procrastinate.SyncPsycopgConnector(conninfo=PROCRASTINATE_DSN)
    app = procrastinate.App(connector=conn)
    with app.open():
        # Apply schema (idempotent — Procrastinate's apply_schema is safe to re-run).
        app.schema_manager.apply_schema()
        yield app


def _fetch_job_args(app, job_id):
    """Read the stored ``args`` JSONB for a Procrastinate job."""
    with app.connector.pool.connection() as conn:
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
    args = _fetch_job_args(app, job_id)
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
    assert fetched.value == 100
    assert fetched.data == {"result": a + b}


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

    args = _fetch_job_args(app, job_id)
    tb_id = args["__taskbadger_task_id__"]

    fetched = taskbadger.get_task(tb_id)
    assert fetched.status == StatusEnum.SUCCESS
