import typer
from rich import print
from rich.console import Console

from taskbadger.exceptions import ConfigurationError


def _configure_api(ctx):
    config = ctx.meta["tb_config"]
    try:
        config.init_api()
    except ConfigurationError as e:
        print(f"[red]{str(e)}[/red]")
        raise typer.Exit(code=1)


err_console = Console(stderr=True)
