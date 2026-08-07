import json
import os
from http import HTTPStatus
from unittest import mock

import pytest
from typer.testing import CliRunner

from taskbadger.cli_main import app
from taskbadger.internal.models import PaginatedTaskList
from taskbadger.internal.types import Response
from tests.utils import task_for_test

runner = CliRunner()

NEXT_URL = "https://taskbadger.net/api/org/project/tasks/?cursor=next-token"


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


def _mock_list(*tasks, next_=None):
    page = PaginatedTaskList(results=list(tasks), next_=next_, previous=None)
    return Response(HTTPStatus.OK, b"", {}, page)


def test_cli_list_pretty():
    with mock.patch("taskbadger.sdk.task_list.sync_detailed") as list_:
        # short id so the rich table doesn't truncate it at the default width
        task = task_for_test(id="t1")
        list_.return_value = _mock_list(task, next_=NEXT_URL)

        result = runner.invoke(app, ["list"])

    assert result.exit_code == 0, result.output
    assert "t1" in result.output
    assert task.name in result.output
    assert "next-token" in result.output


def test_cli_list_json():
    with mock.patch("taskbadger.sdk.task_list.sync_detailed") as list_:
        task = task_for_test()
        list_.return_value = _mock_list(task, next_=NEXT_URL)

        result = runner.invoke(app, ["list", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["next_token"] == "next-token"
    assert [t["id"] for t in payload["results"]] == [task.id]


def test_cli_list_csv():
    with mock.patch("taskbadger.sdk.task_list.sync_detailed") as list_:
        task = task_for_test()
        list_.return_value = _mock_list(task)

        result = runner.invoke(app, ["list", "--format", "csv"])

    assert result.exit_code == 0, result.output
    assert task.id in result.output
    assert "next_token" not in result.output
