import os
from http import HTTPStatus
from unittest import mock

from typer.testing import CliRunner

from taskbadger.cli import app
from taskbadger.internal.models import PatchedTaskRequest, PatchedTaskRequestData, StatusEnum, TaskRequest
from taskbadger.internal.types import Response
from taskbadger.sdk import _get_settings
from tests.utils import task_for_test

runner = CliRunner()


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_cli_run_success():
    _test_cli_run(["echo", "test"], 0)


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_cli_long_run():
    def _should_update_task(last_update, update_frequency_seconds):
        return True

    with mock.patch("taskbadger.cli._should_update_task", new=_should_update_task):
        _test_cli_run(["echo test; sleep 0.11"], 0, update_call_count=3)


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_cli_run_error():
    _test_cli_run(["not-a-command"], 127)


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_cli_run():
    _test_cli_run(
        ["echo test"],
        0,
        ["-a", "success,error", "email", "to:me@test.com"],
        action={"trigger": "success,error", "integration": "email", "config": {"to": "me@test.com"}},
    )


def _test_cli_run(command, return_code, args=None, action=None, update_call_count=1):
    with (
        mock.patch("taskbadger.sdk.task_create.sync_detailed") as create,
        mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as update,
    ):
        task = task_for_test()
        create.return_value = Response(HTTPStatus.OK, b"", {}, task)

        update.return_value = Response(HTTPStatus.OK, b"", {}, task)
        args = args or []
        result = runner.invoke(app, ["run", "task_name"] + args + ["--"] + command, catch_exceptions=False)
        assert result.exit_code == return_code, result.output

        settings = _get_settings()
        request = TaskRequest(name="task_name", status=StatusEnum.PROCESSING, stale_timeout=10)
        if action:
            request.additional_properties = {"actions": [action]}
        create.assert_called_with(
            client=settings.client, organization_slug="org", project_slug="project", json_body=request
        )

        if return_code == 0:
            body = PatchedTaskRequest(status=StatusEnum.SUCCESS, value=100)
        else:
            body = PatchedTaskRequest(
                status=StatusEnum.ERROR, data=PatchedTaskRequestData.from_dict({"return_code": return_code})
            )

        assert update.call_count == update_call_count
        update.assert_called_with(
            client=settings.client, organization_slug="org", project_slug="project", id="test_id", json_body=body
        )
