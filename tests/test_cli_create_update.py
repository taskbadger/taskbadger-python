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
    TaskRequestDataType0,
)
from taskbadger.internal.types import Response
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


def test_cli_create():
    with (
        mock.patch("taskbadger.sdk.task_create.sync_detailed") as create,
    ):
        task = task_for_test()
        create.return_value = Response(HTTPStatus.OK, b"", {}, task)

        args = [
            "create",
            "my-task",
            "--metadata-json",
            '{"a": 1, "c": 1}',
            "--metadata",
            "b=2",
            "--metadata",
            "a=3",
        ]
        result = runner.invoke(app, args, catch_exceptions=False)
        assert result.exit_code == 0, result.output

        request = TaskRequest(
            name="my-task",
            status=StatusEnum.PROCESSING,
            value_max=100,
            data=TaskRequestDataType0.from_dict({"b": "2", "a": 1, "c": 1}),
        )
        create.assert_called_with(
            client=mock.ANY,
            organization_slug="org",
            project_slug="project",
            body=request,
        )


def test_cli_update():
    with mock.patch("taskbadger.sdk.task_partial_update.sync_detailed") as update:
        task = task_for_test()
        update.return_value = Response(HTTPStatus.OK, b"", {}, task)

        result = runner.invoke(
            app,
            ["update", "task123", "--status=success", "--value", "100"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        body = PatchedTaskRequest(status=StatusEnum.SUCCESS, value=100)

        update.assert_called_with(
            client=mock.ANY,
            organization_slug="org",
            project_slug="project",
            id="task123",
            body=body,
        )
