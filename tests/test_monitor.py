import os
from datetime import datetime
from http import HTTPStatus
from unittest import mock

from typer.testing import CliRunner

from taskbadger.cli import app
from taskbadger.internal.models import Task, TaskRequest, StatusEnum, PatchedTaskRequest, PatchedTaskRequestData
from taskbadger.internal.types import Response
from taskbadger.sdk import _get_settings

runner = CliRunner()

@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org",
    "TASKBADGER_PROJECT": "project",
    "TASKBADGER_TOKEN": "token",
}, clear=True)
def test_monitor_success():
    _test_monitor(["echo", "test"], 0)


@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org",
    "TASKBADGER_PROJECT": "project",
    "TASKBADGER_TOKEN": "token",
}, clear=True)
def test_monitor_error():
    _test_monitor(["not-a-command"], 127)


def _test_monitor(command, return_code):
    with (
        mock.patch("taskbadger.sdk.task_create.sync_detailed") as create,
        mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as update
    ):
        task = Task("task_id", "org", "project", "task_name", datetime.utcnow(), datetime.utcnow(), None)
        create.return_value = Response(HTTPStatus.OK, b"", {}, task)

        update.return_value = Response(HTTPStatus.OK, b"", {}, task)
        result = runner.invoke(app, ["monitor", "task_name", "--"] + command)
        assert result.exit_code == return_code

        settings = _get_settings()
        create.assert_called_with(
            client=settings.client,
            organization_slug="org",
            project_slug="project",
            json_body=TaskRequest(name="task_name", status=StatusEnum.PENDING)
        )

        if return_code == 0:
            body = PatchedTaskRequest(status=StatusEnum.SUCCESS)
        else:
            body = PatchedTaskRequest(
                status=StatusEnum.ERROR,
                data=PatchedTaskRequestData.from_dict({'return_code': return_code})
            )

        update.assert_called_with(
            client=settings.client,
            organization_slug="org",
            project_slug="project",
            id="task_id",
            json_body=body
        )
