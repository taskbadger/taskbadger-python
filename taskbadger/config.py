import dataclasses
import inspect
import os
from pathlib import Path

import tomlkit
import typer
from tomlkit import document, table

from taskbadger.sdk import _TB_HOST, _init

APP_NAME = "taskbadger"


@dataclasses.dataclass
class Config:
    token: str = None
    organization_slug: str = None
    project_slug: str = None
    host: str = _TB_HOST

    def is_valid(self):
        return bool(self.token and self.organization_slug and self.project_slug)

    def init_api(self):
        _init(self.host, self.organization_slug, self.project_slug, self.token)

    @staticmethod
    def from_dict(config_dict, **overrides) -> "Config":
        """Compile the config from the various sources.

        Arguments:
            config_dict:
                Dictionary of configuration values that come from the
                configuration file.
            **overrides:
                These values take precedence over any others.
                Typically, they come from the command line arguments.

        Config is loaded from 3 places. If a value is present in all three, the
        value with the highest precedence will be used. The order of precedence is
        as follows (low to high):
        1. Config file
        2. Environment variables
        3. Command line arguments
        """
        defaults = config_dict.get("defaults", {})
        auth = config_dict.get("auth", {})
        return Config(
            token=overrides.get("token") or _from_env("API_KEY", auth.get("token")),
            organization_slug=overrides.get("org") or _from_env("ORG", defaults.get("org")),
            project_slug=overrides.get("project") or _from_env("PROJECT", defaults.get("project")),
            host=overrides.get("host") or auth.get("host"),
        )

    def __str__(self):
        host = ""
        if self.host != _TB_HOST:
            host = f"\n            Host: {self.host}"
        return inspect.cleandoc(
            f"""
            Organization slug: {self.organization_slug or "-"}
            Project slug: {self.project_slug or "-"}
            Auth token: {self.token or "-"}{host}
            """
        )


def _from_env(name, default=None, prefix="TASKBADGER_"):
    return os.environ.get(f"{prefix}{name}", default)


def write_config(config):
    doc = document()

    doc.add(
        "defaults",
        table().add("org", config.organization_slug).add("project", config.project_slug),
    )

    doc.add("auth", table().add("token", config.token))

    config_path = _get_config_path()
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True)
    with config_path.open("wt", encoding="utf-8") as fp:
        tomlkit.dump(doc, fp)

    return config_path


def get_config(**overrides):
    """Get the CLI config.
    See `Config.from_dict` for details about precedence.
    """
    config_dict = {}
    config_path = _get_config_path()
    if config_path.is_file():
        with config_path.open("rt", encoding="utf-8") as fp:
            raw_config = tomlkit.load(fp)
        config_dict = raw_config.unwrap()

    return Config.from_dict(config_dict, **overrides)


def _get_config_path():
    app_dir = typer.get_app_dir(APP_NAME)
    config_path: Path = Path(app_dir) / "config"
    return config_path
