import os
from http import HTTPStatus
from unittest import mock

import pytest
from typer.testing import CliRunner

from taskbadger.cli_main import app
from taskbadger.internal.models import (
    PatchedTaskRequest,
    StatusEnum,
    TaskRequest,
)
from taskbadger.internal.types import UNSET, Response
from taskbadger.mug import Badger
from taskbadger.sdk import Task
from tests.utils import task_for_test

runner = CliRunner()


@pytest.fixture(autouse=True)
def _mock_env():
    with mock.patch.dict(
        os.environ,
        {
            "TASKBADGER_ORG": "org",
            "TASKBADGER_PROJECT": "project",
            "TASKBADGER_API_KEY": "token",
        },
        clear=True,
    ):
        yield


def test_cli_run_success():
    _test_cli_run(["echo", "test"], 0, args=["task_name"])


def test_cli_long_run():
    def _should_update_task(last_update, update_frequency_seconds):
        return True

    with mock.patch("taskbadger.process._should_update", new=_should_update_task):
        _test_cli_run(["echo test; sleep 0.11"], 0, args=["task_name"], update_call_count=3)


def test_cli_capture_output():
    update_patch = _test_cli_run(["echo test"], 0, args=["task_name", "--capture-output"], update_call_count=2)

    body = PatchedTaskRequest(status=UNSET, data={"stdout": "test\n"})
    update_patch.assert_any_call(
        client=mock.ANY,
        organization_slug="org",
        project_slug="project",
        id=mock.ANY,
        body=body,
    )


def test_cli_capture_output_append():
    def _should_update_task(last_update, update_frequency_seconds):
        return True

    with mock.patch("taskbadger.process._should_update", new=_should_update_task):
        update_patch = _test_cli_run(
            ["echo test; sleep 0.11; echo 123"],
            0,
            args=["task_name", "--capture-output"],
            update_call_count=3,
        )

    body = PatchedTaskRequest(status=UNSET, data={"stdout": "test\n123\n"})
    update_patch.assert_any_call(
        client=mock.ANY,
        organization_slug="org",
        project_slug="project",
        id=mock.ANY,
        body=body,
    )


def test_cli_run_error():
    _test_cli_run(["not-a-command"], 127, args=["task_name"])


def test_cli_run():
    _test_cli_run(
        ["echo test"],
        0,
        ["task_name", "-a", "success,error", "email", "to:me@test.com"],
        action={
            "trigger": "success,error",
            "integration": "email",
            "config": {"to": "me@test.com"},
        },
    )


def test_cli_run_webhook():
    _test_cli_run(
        ["echo test"],
        0,
        ["task_name", "-a", "cancelled", "webhook:123", ""],
        action={"trigger": "cancelled", "integration": "webhook:123", "config": {}},
    )


def _test_cli_run(command, return_code, args=None, action=None, update_call_count=1):
    update_mock = mock.MagicMock()

    def _update(*args, **kwargs):
        task_id = kwargs["id"]
        update_mock(*args, **kwargs)

        # handle updating task data
        data = kwargs["body"].data
        task_return = task_for_test(id=task_id, data=data if data else None)
        return Response(HTTPStatus.OK, b"", {}, task_return)

    with (
        mock.patch("taskbadger.sdk.task_create.sync_detailed") as create,
        mock.patch("taskbadger.sdk.task_partial_update.sync_detailed", new=_update),
    ):
        task = task_for_test()
        create.return_value = Response(HTTPStatus.OK, b"", {}, task)

        args = args or []
        result = runner.invoke(app, ["run"] + args + ["--"] + command, catch_exceptions=False)
        print(result.output)
        assert result.exit_code == return_code, result.output

        request = TaskRequest(name="task_name", status=StatusEnum.PROCESSING, stale_timeout=10)
        if action:
            request.additional_properties = {"actions": [action]}
        create.assert_called_with(
            client=mock.ANY,
            organization_slug="org",
            project_slug="project",
            body=request,
        )

        if return_code == 0:
            body = PatchedTaskRequest(status=StatusEnum.SUCCESS, value=100)
        else:
            body = PatchedTaskRequest(
                status=StatusEnum.ERROR,
                data={"return_code": return_code},
            )

        assert update_mock.call_count == update_call_count
        update_mock.assert_called_with(
            client=mock.ANY,
            organization_slug="org",
            project_slug="project",
            id=task.id,
            body=body,
        )
        return update_mock


def test_cli_run_session():
    def _update(*args, **kwargs):
        session = Badger.current.session()
        assert session.client is not None, "Session is not set"
        return Task(task_for_test())

    def _create(*args, **kwargs):
        session = Badger.current.session()
        assert session.client is not None, "Session is not set"
        return Task(task_for_test())

    with (
        mock.patch("taskbadger.sdk.create_task", new=_create),
        mock.patch("taskbadger.sdk.update_task", new=_update),
        mock.patch("taskbadger.cli.wrapper.err_console") as err,
    ):
        args = ["task_name"]
        result = runner.invoke(app, ["run"] + args + ["--"] + ["echo", "test"], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert err.print.call_count == 0, err.print.call_args_list
