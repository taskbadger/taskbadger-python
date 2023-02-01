import dataclasses
import inspect
import os
from pathlib import Path

import tomlkit
import typer
from tomlkit import document, table

import taskbadger as tb

APP_NAME = "taskbadger"


@dataclasses.dataclass
class Config:
    token: str = None
    organization_slug: str = None
    project_slug: str = None

    def is_valid(self):
        return bool(self.token and self.organization_slug and self.project_slug)

    def init_api(self):
        tb.init(self.organization_slug, self.project_slug, self.token)

    @staticmethod
    def from_dict(config_dict, **overrides) -> "Config":
        defaults = config_dict.get("defaults", {})
        auth = config_dict.get("auth", {})
        return Config(
            token=overrides.get("token") or _from_env("TOKEN", auth.get("token")),
            organization_slug=overrides.get("org") or _from_env("ORG", defaults.get("org")),
            project_slug=overrides.get("project") or _from_env("PROJECT", defaults.get("project")),
        )

    def __str__(self):
        return inspect.cleandoc(
            f"""
            Organization slug: {self.organization_slug or '-'}
            Project slug: {self.project_slug or '-'}
            Auth token: {self.token or '-'}
            """
        )


def _from_env(name, default=None, prefix="TASKBADGER_"):
    return os.environ.get(f"{prefix}{name}", default)


def write_config(config):
    doc = document()

    doc.add("defaults", table().add("org", config.organization_slug).add("project", config.project_slug))

    doc.add("auth", table().add("token", config.token))

    config_path = _get_config_path()
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True)
    with config_path.open("wt", encoding="utf-8") as fp:
        tomlkit.dump(doc, fp)

    return config_path


def get_config(**overrides):
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
