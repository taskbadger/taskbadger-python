import base64
import os
from pathlib import Path
from unittest import mock

import pytest
import tomlkit
from typer.testing import CliRunner

from taskbadger.cli_main import app
from taskbadger.config import Config
from taskbadger.mug import Badger, _local
from taskbadger.sdk import _parse_token, init


def _make_project_key(org="myorg", project="myproject", key="secret123"):
    return base64.b64encode(f"{org}/{project}/{key}".encode()).decode()


# --- _parse_token tests ---


class TestParseToken:
    def test_valid_project_key(self):
        token = _make_project_key("org1", "proj1", "apikey")
        result = _parse_token(token)
        assert result == ("org1", "proj1", "apikey")

    def test_legacy_key(self):
        result = _parse_token("some-legacy-api-key")
        assert result is None

    def test_invalid_base64(self):
        result = _parse_token("!!!not-base64!!!")
        assert result is None

    def test_base64_but_wrong_format_two_parts(self):
        token = base64.b64encode(b"only/two").decode()
        result = _parse_token(token)
        assert result is None

    def test_base64_but_wrong_format_four_parts(self):
        token = base64.b64encode(b"a/b/c/d").decode()
        result = _parse_token(token)
        assert result is None

    def test_base64_with_empty_parts(self):
        token = base64.b64encode(b"org//key").decode()
        result = _parse_token(token)
        assert result is None

    def test_empty_string(self):
        result = _parse_token("")
        assert result is None


# --- init() tests ---


@pytest.fixture(autouse=True)
def _reset_badger():
    b_global = Badger.current
    _local.set(Badger())
    yield
    _local.set(b_global)


class TestInitWithProjectKey:
    def test_init_with_project_key(self):
        token = _make_project_key("org1", "proj1", "apikey")
        init(token=token)
        settings = Badger.current.settings
        assert settings.organization_slug == "org1"
        assert settings.project_slug == "proj1"
        assert settings.token == "apikey"

    def test_init_project_key_overrides_org_project(self):
        token = _make_project_key("org1", "proj1", "apikey")
        init(organization_slug="ignored", project_slug="ignored", token=token)
        settings = Badger.current.settings
        assert settings.organization_slug == "org1"
        assert settings.project_slug == "proj1"
        assert settings.token == "apikey"

    def test_init_project_key_via_env(self):
        token = _make_project_key("org1", "proj1", "apikey")
        with mock.patch.dict(os.environ, {"TASKBADGER_API_KEY": token}):
            init()
        settings = Badger.current.settings
        assert settings.organization_slug == "org1"
        assert settings.project_slug == "proj1"
        assert settings.token == "apikey"

    def test_init_project_key_no_deprecation_warning(self, recwarn):
        token = _make_project_key()
        init(token=token)
        deprecation_warnings = [w for w in recwarn if issubclass(w.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0

    def test_init_legacy_key_emits_deprecation_warning(self):
        with pytest.warns(DeprecationWarning, match="Legacy API keys are deprecated"):
            init("org", "project", "legacy-token")

    def test_init_legacy_key_still_works(self):
        with pytest.warns(DeprecationWarning):
            init("org", "project", "legacy-token")
        settings = Badger.current.settings
        assert settings.organization_slug == "org"
        assert settings.project_slug == "project"
        assert settings.token == "legacy-token"


# --- Config.from_dict tests ---


class TestConfigFromDictWithProjectKey:
    def test_project_key_in_config(self):
        token = _make_project_key("org1", "proj1", "apikey")
        config = Config.from_dict({"auth": {"token": token}})
        assert config.organization_slug == "org1"
        assert config.project_slug == "proj1"
        # Token remains as original base64 string (decoded by _init at init time)
        assert config.token == token

    def test_project_key_overrides_config_org_project(self):
        token = _make_project_key("org1", "proj1", "apikey")
        config = Config.from_dict(
            {
                "auth": {"token": token},
                "defaults": {"org": "old-org", "project": "old-project"},
            }
        )
        assert config.organization_slug == "org1"
        assert config.project_slug == "proj1"

    def test_project_key_via_env(self):
        token = _make_project_key("org1", "proj1", "apikey")
        with mock.patch.dict(os.environ, {"TASKBADGER_API_KEY": token}):
            config = Config.from_dict({})
        assert config.organization_slug == "org1"
        assert config.project_slug == "proj1"
        assert config.token == token

    def test_project_key_is_valid(self):
        token = _make_project_key("org1", "proj1", "apikey")
        config = Config.from_dict({"auth": {"token": token}})
        assert config.is_valid()


# --- CLI configure tests ---

runner = CliRunner()


@pytest.fixture()
def mock_config_location():
    config_path = Path(__file__).parent / "_mock_config_project_key"
    with mock.patch("taskbadger.config._get_config_path", return_value=config_path):
        yield config_path
    if config_path.exists():
        os.remove(config_path)


class TestCLIConfigureProjectKey:
    def test_configure_with_project_key(self, mock_config_location):
        token = _make_project_key("myorg", "myproj", "mykey")
        result = runner.invoke(app, ["configure"], input=f"{token}\n")
        assert result.exit_code == 0
        assert "Project key detected" in result.stdout
        assert "myorg" in result.stdout
        assert "myproj" in result.stdout

        with mock_config_location.open("rt", encoding="utf-8") as fp:
            raw_config = tomlkit.load(fp)
        config_dict = raw_config.unwrap()
        assert config_dict["defaults"]["org"] == "myorg"
        assert config_dict["defaults"]["project"] == "myproj"
        assert config_dict["auth"]["token"] == token

    def test_configure_with_legacy_key(self, mock_config_location):
        result = runner.invoke(app, ["configure"], input="a-token\nan-org\na-project\n")
        assert result.exit_code == 0
        assert "Project key detected" not in result.stdout

        with mock_config_location.open("rt", encoding="utf-8") as fp:
            raw_config = tomlkit.load(fp)
        config_dict = raw_config.unwrap()
        assert config_dict["defaults"]["org"] == "an-org"
        assert config_dict["defaults"]["project"] == "a-project"
        assert config_dict["auth"]["token"] == "a-token"
