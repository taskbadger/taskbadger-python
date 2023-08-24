from typing import Optional, Tuple

import typer
from rich import print
from rich.console import Console

from taskbadger import Action, DefaultMergeStrategy, Session, StatusEnum, Task, __version__, integrations
from taskbadger.config import get_config, write_config
from taskbadger.exceptions import ConfigurationError
from taskbadger.process import ProcessRunner

app = typer.Typer(
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


err_console = Console(stderr=True)


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


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": False})
def run(
    ctx: typer.Context,
    name: str,
    monitor_id: str = typer.Option(None, help="Associate this task with a monitor."),
    update_frequency: int = typer.Option(5, metavar="SECONDS", min=5, max=300, help="Seconds between updates."),
    action_def: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help="Action definition e.g. 'success,error email to:me@email.com'",
    ),
    capture_output: bool = typer.Option(False, help="Capture stdout and stderr."),
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
    if any(action_def):
        trigger, integration, config = action_def
        action = Action(trigger, integrations.from_config(integration, config))
    stale_timeout = update_frequency * 2
    with Session():
        try:
            task = Task.create(
                name,
                status=StatusEnum.PROCESSING,
                stale_timeout=stale_timeout,
                actions=[action] if action else None,
                monitor_id=monitor_id,
            )
        except Exception as e:
            err_console.print(f"Error creating task: {e}")
            task = None
        else:
            print(f"Task created: {task.public_url}")
        env = {"TASKBADGER_TASK_ID": task.id} if task else None
        try:
            process = ProcessRunner(ctx.args, env, capture_output=capture_output, update_frequency=update_frequency)
            for output in process.run():
                _update_task(task, **(output or {}))
        except Exception as e:
            _update_task(task, exception=str(e))
            raise typer.Exit(1)

        if task:
            if process.returncode == 0:
                task.success(value=100)
            else:
                _update_task(task, status=StatusEnum.ERROR, return_code=process.returncode)

    if process.returncode != 0:
        raise typer.Exit(process.returncode)


def _update_task(task, status=None, **data_kwargs):
    """Update the task and merge the data"""
    if not task:
        return

    merge_strategy = DefaultMergeStrategy(append_keys=("stdout", "stderr"))
    try:
        task.update(status=status, data=data_kwargs or None, data_merge_strategy=merge_strategy)
    except Exception as e:
        err_console.print(f"Error updating task status: {e!r}")


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
