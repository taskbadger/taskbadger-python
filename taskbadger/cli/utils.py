import json
from enum import Enum

import typer
from rich import print
from rich.console import Console

from taskbadger import Action, integrations
from taskbadger.exceptions import ConfigurationError


def configure_api(ctx):
    config = ctx.meta["tb_config"]
    try:
        config.init_api()
    except ConfigurationError as e:
        print(f"[red]{str(e)}[/red]")
        raise typer.Exit(code=1)


err_console = Console(stderr=True)


def get_actions(action_def: tuple[str, str, str]) -> list[Action]:
    if any(action_def):
        trigger, integration, config = action_def
        return [Action(trigger, integrations.from_config(integration, config))]
    return []


def merge_kv_json(metadata_kv: list[str], metadata_json: str) -> dict:
    metadata = {}
    for kv in metadata_kv:
        k, v = kv.strip().split("=", 1)
        metadata[k] = v

    if metadata_json:
        metadata.update(json.loads(metadata_json))

    return metadata


class OutputFormat(str, Enum):
    pretty = "pretty"
    json = "json"
    csv = "csv"
