import os
from datetime import datetime
from http import HTTPStatus
from unittest import mock

from typer.testing import CliRunner

from taskbadger.cli import app
from taskbadger.internal.models import PatchedTaskRequest, PatchedTaskRequestData, StatusEnum, Task, TaskRequest
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
def test_monitor_success():
    _test_monitor(["echo", "test"], 0)


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_monitor_error():
    _test_monitor(["not-a-command"], 127)


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org",
        "TASKBADGER_PROJECT": "project",
        "TASKBADGER_TOKEN": "token",
    },
    clear=True,
)
def test_monitor_action():
    _test_monitor(
        ["echo", "test"],
        0,
        ["-a", "success,error", "email", "to:me@test.com"],
        action={"trigger": "success,error", "integration": "email", "config": {"to": "me@test.com"}},
    )


def _test_monitor(command, return_code, args=None, action=None):
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
        request = TaskRequest(name="task_name", status=StatusEnum.PENDING)
        if action:
            request.additional_properties = {"actions": [action]}
        create.assert_called_with(
            client=settings.client, organization_slug="org", project_slug="project", json_body=request
        )

        if return_code == 0:
            body = PatchedTaskRequest(status=StatusEnum.SUCCESS)
        else:
            body = PatchedTaskRequest(
                status=StatusEnum.ERROR, data=PatchedTaskRequestData.from_dict({"return_code": return_code})
            )

        update.assert_called_with(
            client=settings.client, organization_slug="org", project_slug="project", id="test_id", json_body=body
        )
