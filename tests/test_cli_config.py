import os
from pathlib import Path
from unittest import mock

import pytest
import tomlkit
from typer.testing import CliRunner

from taskbadger.cli import app
from taskbadger.config import Config, write_config

runner = CliRunner()


@pytest.fixture
def mock_config_location():
    config_path = Path(__file__).parent / "_mock_config"
    with mock.patch("taskbadger.config._get_config_path", return_value=config_path):
        yield config_path
    if config_path.exists():
        os.remove(config_path)


@pytest.fixture
def mock_config(mock_config_location):
    config = Config(organization_slug="test_org", project_slug="test_project", token="test_token")
    write_config(config)


def test_info_blank():
    result = runner.invoke(app, ["info"])
    _check_output(result, "-", "-", "-")


def test_info_args():
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "-")


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org2",
        "TASKBADGER_PROJECT": "project2",
        "TASKBADGER_TOKEN": "123",
    },
    clear=True,
)
def test_info_env():
    result = runner.invoke(app, ["info"])
    _check_output(result, "org2", "project2", "123")


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org2",
        "TASKBADGER_PROJECT": "project2",
    },
    clear=True,
)
def test_info_args_trump_env():
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "-")


def test_info_config(mock_config):
    result = runner.invoke(app, ["info"])
    _check_output(result, "test_org", "test_project", "test_token")


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org2",
        "TASKBADGER_PROJECT": "project2",
        "TASKBADGER_TOKEN": "token2",
    },
    clear=True,
)
def test_info_config_env(mock_config):
    result = runner.invoke(app, ["info"])
    _check_output(result, "org2", "project2", "token2")


def test_info_config_args(mock_config):
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "test_token")


@mock.patch.dict(
    os.environ,
    {
        "TASKBADGER_ORG": "org2",
        "TASKBADGER_PROJECT": "project2",
        "TASKBADGER_TOKEN": "token2",
    },
    clear=True,
)
def test_info_config_env_args(mock_config):
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "token2")


def test_configure(mock_config_location):
    result = runner.invoke(app, ["configure"], input="an-org\na-project\na-token")
    assert result.exit_code == 0
    assert mock_config_location.is_file()
    with mock_config_location.open("rt", encoding="utf-8") as fp:
        raw_config = tomlkit.load(fp)
    config_dict = raw_config.unwrap()
    assert config_dict == {
        "defaults": {
            "org": "an-org",
            "project": "a-project",
        },
        "auth": {"token": "a-token"},
    }


def _check_output(result, org, project, token):
    assert result.exit_code == 0
    assert f"Organization slug: {org}" in result.stdout
    assert f"Project slug: {project}" in result.stdout
    assert f"Auth token: {token}" in result.stdout
