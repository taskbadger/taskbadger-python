from typing import Optional

import typer
from rich import print

from taskbadger import __version__
from taskbadger.cli import create, get, list_tasks_command, run, update
from taskbadger.config import get_config, write_config

app = typer.Typer(
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": False})(run)
app.command(context_settings={"ignore_unknown_options": False})(get)
app.command(context_settings={"ignore_unknown_options": False})(create)
app.command(context_settings={"ignore_unknown_options": False})(update)
app.command("list", context_settings={"ignore_unknown_options": False})(list_tasks_command)


def version_callback(value: bool):
    if value:
        print(f"Task Badger CLI Version: {__version__}")
        raise typer.Exit()


@app.command()
def configure(ctx: typer.Context):
    """Update CLI configuration."""
    config = ctx.meta["tb_config"]
    config.organization_slug = typer.prompt(f"Organization slug", default=config.organization_slug)
    config.project_slug = typer.prompt(f"Project slug", default=config.project_slug)
    config.token = typer.prompt(f"API Key", default=config.token)
    path = write_config(config)
    print(f"Config written to [green]{path}[/green]")


@app.command()
def docs():
    """Open Task Badger docs in a browser."""
    typer.launch("https://docs.taskbadger.net")


@app.command()
def info(ctx: typer.Context):
    """Show CLI configuration."""
    config = ctx.meta["tb_config"]
    print(str(config))


@app.callback()
def main(
    ctx: typer.Context,
    org: Optional[str] = typer.Option(
        None,
        "--org",
        "-o",
        metavar="TASKBADGER_ORG",
        show_default=False,
        help="Organization Slug. This will override values from the config file and environment variables.",
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        show_envvar=False,
        metavar="TASKBADGER_PROJECT",
        show_default=False,
        help="Project Slug. This will override values from the config file and environment variables.",
    ),
    version: Optional[bool] = typer.Option(  # noqa
        None, "--version", callback=version_callback, is_eager=True, help="Show CLI Version"
    ),
):
    """
    Task Badger CLI
    """
    config = get_config(org=org, project=project)
    ctx.meta["tb_config"] = config


if __name__ == "__main__":
    app()
