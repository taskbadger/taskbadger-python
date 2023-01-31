import subprocess
from typing import Optional

import typer
from rich import print

import taskbadger as tb
from taskbadger.config import get_config, write_config
from taskbadger.exceptions import ConfigurationError

app = typer.Typer()


def _configure_api(ctx):
    config = ctx.meta["tb_config"]
    try:
        config.init_api()
    except ConfigurationError as e:
        print(f"[red]{str(e)}[/red]")
        raise typer.Exit(code=1)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def monitor(ctx: typer.Context, name: str):
    _configure_api(ctx)
    task = tb.Task.create(name)
    result = subprocess.run(ctx.args, env={"TASKBADGER_TASK_ID": task.id})
    if result.returncode != 0:
        task.success()
    else:
        task.error(data={"return_code": result.returncode})


@app.command()
def configure(ctx: typer.Context):
    config = ctx.meta["tb_config"]
    config.token = typer.prompt(f"Token", default=config.token)
    config.organization_slug = typer.prompt(f"Organization slug", default=config.organization_slug)
    config.project_slug = typer.prompt(f"Project slug", default=config.project_slug)
    path = write_config(config)
    print(f"Config written to [green]{path}[/green]")


@app.command()
def docs():
    typer.launch("https://docs.taskbadger.net")


@app.command()
def info(ctx: typer.Context):
    config = ctx.meta["tb_config"]
    print(f"Default Organization: {config.organization_slug or '-'}")
    print(f"Default Project: {config.project_slug or '-'}")
    print(f"Auth Token: {config.token or '-'}")


@app.callback()
def main(
    ctx: typer.Context,
    org: Optional[str] = typer.Option(None, "--org", "-o", metavar="ORG"),
    project: Optional[str] = typer.Option(None, "--project", "-p", show_envvar=False, metavar="PROJECT"),
):
    """
    Manage users in the awesome CLI app.
    """
    config = get_config(org=org, project=project)
    ctx.meta["tb_config"] = config


if __name__ == "__main__":
    app()
