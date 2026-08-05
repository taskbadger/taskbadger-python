from unittest import mock

import pytest

from taskbadger import StatusEnum
from taskbadger._error_context import capture_error_data
from taskbadger.celery import (
    TB_ERROR_CTX_TOKEN,
    TB_TASK_ID,
    Task,
    task_failure_handler,
    task_postrun_handler,
    task_prerun_handler,
)
from taskbadger.context_providers import ContextProvider
from taskbadger.mug import Badger
from tests.utils import task_for_test


@pytest.mark.usefixtures("_bind_settings")
def test_celery_task_error(celery_session_app, celery_session_worker):
    @celery_session_app.task(bind=True, base=Task)
    def add_error(self, a, b):
        assert self.taskbadger_task is not None
        assert Badger.current.session().client is not None
        raise Exception("error")

    celery_session_worker.reload()

    with (
        mock.patch("taskbadger.celery.create_task_safe") as create,
        mock.patch("taskbadger.celery.update_task_safe") as update,
        mock.patch("taskbadger.sdk.get_task") as get_task,
    ):
        task = task_for_test()
        create.return_value = task
        get_task.return_value = task
        update.return_value = task
        result = add_error.delay(2, 2)
        with pytest.raises(Exception, match="error"):
            result.get(timeout=10, propagate=True)

    create.assert_called()
    update.assert_has_calls(
        [
            mock.call(mock.ANY, status=StatusEnum.PROCESSING, data=mock.ANY),
            mock.call(mock.ANY, status=StatusEnum.ERROR, data=mock.ANY),
        ]
    )
    data_kwarg = update.call_args_list[1][1]["data"]
    assert "Traceback" in data_kwarg["exception"]
    assert Badger.current.session().client is None


class _FakeRequest(dict):
    """Minimal stand-in for Celery's request `Context`: dict-like plus a
    `.headers` attribute, which is all `_get_taskbadger_task_id` needs."""

    headers = None


class _FakeEinfo:
    """Minimal stand-in for Celery's `ExceptionInfo`: wraps the exception and
    renders a traceback-shaped string, mirroring what `task_failure`/`task_retry`
    signals actually pass to `_update_task`."""

    def __init__(self, exc):
        self.exception = exc

    def __str__(self):
        return f"Traceback (most recent call last):\n{self.exception!r}"


@pytest.mark.usefixtures("_bind_settings")
def test_signal_handlers_wire_context_provider_snapshot_to_failure():
    """`task_prerun_handler` snapshots providers and stashes the token on the
    request; `task_failure_handler` should see that exact snapshot when
    building error data; `task_postrun_handler` then resets it."""

    seen_snapshots = []

    class TrackingProvider(ContextProvider):
        identifier = "tracking"

        def snapshot(self):
            return "baseline"

        def capture_error_context(self, exception, snapshot=None):
            seen_snapshots.append(snapshot)
            return {"snapshot": snapshot}

    Badger.current.settings.context_providers = [TrackingProvider()]

    sender = mock.Mock()
    sender.request = _FakeRequest({TB_TASK_ID: "tb-1"})
    task = task_for_test(id="tb-1", status=StatusEnum.PROCESSING)
    sender.taskbadger_task = task

    with (
        mock.patch("taskbadger.celery.safe_get_task", return_value=task),
        mock.patch("taskbadger.celery.update_task_safe", return_value=task) as update,
        mock.patch("taskbadger.celery.enter_session"),
        mock.patch("taskbadger.celery.exit_session"),
    ):
        task_prerun_handler(sender=sender)
        assert TB_ERROR_CTX_TOKEN in sender.request

        task_failure_handler(sender=sender, einfo=_FakeEinfo(ValueError("boom")))
        task_postrun_handler(sender=sender)

    # The snapshot seen at failure time is the one taken at prerun, not a
    # missing/None one -- proving the token round-trips through the request.
    assert seen_snapshots == ["baseline"]
    data_kwarg = update.call_args.kwargs["data"]
    assert data_kwarg["tracking"] == {"snapshot": "baseline"}


@pytest.mark.usefixtures("_bind_settings")
def test_postrun_resets_context_after_error():
    """Once `task_postrun_handler` runs, a later error in the same thread with
    no provider snapshot taken shouldn't see a stale one left over from the
    previous task."""

    class TrackingProvider(ContextProvider):
        identifier = "tracking"

        def snapshot(self):
            return "baseline"

        def capture_error_context(self, exception, snapshot=None):
            return {"snapshot": snapshot}

    Badger.current.settings.context_providers = [TrackingProvider()]

    task = task_for_test(id="tb-2", status=StatusEnum.PROCESSING)
    sender = mock.Mock()
    sender.request = _FakeRequest({TB_TASK_ID: "tb-2"})
    sender.taskbadger_task = task

    with (
        mock.patch("taskbadger.celery.safe_get_task", return_value=task),
        mock.patch("taskbadger.celery.update_task_safe", return_value=task),
        mock.patch("taskbadger.celery.enter_session"),
        mock.patch("taskbadger.celery.exit_session"),
    ):
        task_prerun_handler(sender=sender)
        task_postrun_handler(sender=sender)

    # A failure reported outside of any tracked task's prerun/postrun window
    # (e.g. directly via Task.error) has no snapshot to compare against.
    data = capture_error_data(ValueError("boom"))
    assert data["tracking"] == {"snapshot": None}
