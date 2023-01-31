import os
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from taskbadger.cli import app
from taskbadger.config import write_config, Config

runner = CliRunner()


@pytest.fixture
def test_config():
    app_dir = Path(__file__).parent / "_test_config"
    with mock.patch("taskbadger.config._get_config_path", return_value=app_dir):
        config = Config(organization_slug="test_org", project_slug="test_project", token="test_token")
        write_config(config)
        yield
        os.remove(app_dir)


def test_info_blank():
    result = runner.invoke(app, ["info"])
    _check_output(result, "-", "-", "-")


def test_info_args():
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "-")


@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org2",
    "TASKBADGER_PROJECT": "project2",
    "TASKBADGER_TOKEN": "123",
}, clear=True)
def test_info_env():
    result = runner.invoke(app, ["info"])
    _check_output(result, "org2", "project2", "123")


@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org2",
    "TASKBADGER_PROJECT": "project2",
}, clear=True)
def test_info_args_trump_env():
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "-")


def test_info_config(test_config):
    result = runner.invoke(app, ["info"])
    _check_output(result, "test_org", "test_project", "test_token")


@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org2",
    "TASKBADGER_PROJECT": "project2",
    "TASKBADGER_TOKEN": "token2",
}, clear=True)
def test_info_config_env(test_config):
    result = runner.invoke(app, ["info"])
    _check_output(result, "org2", "project2", "token2")


def test_info_config_args(test_config):
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "test_token")


@mock.patch.dict(os.environ, {
    "TASKBADGER_ORG": "org2",
    "TASKBADGER_PROJECT": "project2",
    "TASKBADGER_TOKEN": "token2",
}, clear=True)
def test_info_config_env_args(test_config):
    result = runner.invoke(app, ["-o", "org1", "-p", "project1", "info"])
    _check_output(result, "org1", "project1", "token2")


def _check_output(result, org, project, token):
    assert result.exit_code == 0
    assert f"Organization slug: {org}" in result.stdout
    assert f"Project slug: {project}" in result.stdout
    assert f"Auth token: {token}" in result.stdout
