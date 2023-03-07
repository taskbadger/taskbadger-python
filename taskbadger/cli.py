import subprocess
from typing import Optional, Tuple

import typer
from rich import print

from taskbadger import Task, Action, integrations
from taskbadger.config import get_config, write_config
from taskbadger.exceptions import ConfigurationError

app = typer.Typer(rich_markup_mode="rich")

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    __version__ = "dev"


def version_callback(value: bool):
    if value:
        print(f"Task Badger CLI Version: {__version__}")
        raise typer.Exit()


def _configure_api(ctx):
    config = ctx.meta["tb_config"]
    try:
        config.init_api()
    except ConfigurationError as e:
        print(f"[red]{str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    name: str,
    action_def: Tuple[str, integrations.Integrations, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help='Action definition e.g. "success,error email to:me@email.com"',
    ),
):
    """Execute a command using the CLI and create a Task to track its outcome.

    This command makes it easy to track a process's outcome using Task Badger.

    It will create a Task prior to executing your command and will update
    the Task status when you command exits.

    Example:

        [on black]taskbadger run 'my task' -- ./my-script.sh arg -v[/]
    """
    _configure_api(ctx)
    action = None
    if all(action_def):
        trigger, integration, config = action_def
        action = Action(trigger, integrations.from_config(integration, config))
    task = Task.create(name, actions=[action] if action else None)
    try:
        result = subprocess.run(ctx.args, env={"TASKBADGER_TASK_ID": task.id}, shell=True)
    except Exception as e:
        task.error(data={"exception": str(e)})
        raise typer.Exit(1)

    if result.returncode == 0:
        task.success()
    else:
        task.error(data={"return_code": result.returncode})
        raise typer.Exit(result.returncode)


@app.command()
def configure(ctx: typer.Context):
    """Update CLI configuration."""
    config = ctx.meta["tb_config"]
    config.organization_slug = typer.prompt(f"Organization slug", default=config.organization_slug)
    config.project_slug = typer.prompt(f"Project slug", default=config.project_slug)
    config.token = typer.prompt(f"Token", default=config.token)
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
        None, "--org", "-o", metavar="ORG", show_default=False,
        help="Organization Slug. This will override values from the config file and environment variables."
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", show_envvar=False, metavar="PROJECT", show_default=False,
        help="Project Slug. This will override values from the config file and environment variables."
    ),
    version: Optional[bool] = typer.Option(  # noqa
        None, "--version", callback=version_callback, is_eager=True,
        help="Show CLI Version"
    ),
):
    """
    Task Badger CLI
    """
    config = get_config(org=org, project=project)
    ctx.meta["tb_config"] = config


if __name__ == "__main__":
    app()
