import csv
import json
import sys
from enum import Enum
from urllib.parse import parse_qs, urlparse

import typer
from rich import Console, print
from rich.table import Table

from taskbadger.cli.utils import configure_api
from taskbadger.sdk import list_tasks


class ListFormat(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"

    def render(self, ctx, result):
        if self == ListFormat.table:
            _render_table(ctx, result)
        elif self == ListFormat.json:
            _render_json(ctx, result)
        elif self == ListFormat.csv:
            _render_csv(ctx, result)
        else:
            raise ValueError(f"Unknown format: {self}")


def list_tasks_command(
    ctx: typer.Context,
    output_format: ListFormat = typer.Option(ListFormat.table, "--format", "-f", help="Output format"),
    limit: int = typer.Option(100, help="Limit the number of results."),
    start_token: str = typer.Option(None, show_default=False, help="Start token."),
):
    """List tasks."""
    configure_api(ctx)
    tasks = list_tasks(page_size=limit, cursor=start_token)
    output_format.render(ctx, tasks)


def _render_table(ctx, result):
    table = Table(
        title=f"Project: {ctx.meta['tb_config'].project_slug}, Organization: {ctx.meta['tb_config'].organization_slug}"
    )

    table.add_column("Created", no_wrap=True)
    table.add_column("Name")
    table.add_column("Status", no_wrap=True)
    table.add_column("Percent", no_wrap=True)

    for task in result.results:
        table.add_row(task.created.isoformat(), task.name, task.status, str(task.value_percent))
    Console().print(table)

    cursor = _get_cursor(result.next_)
    if cursor:
        print(f"Next page token: [bold green]'{cursor}'[/]")


def _render_csv(ctx, result):
    writer = csv.writer(sys.stdout)
    writer.writerow("Created,Name,Status,Percent".split(","))
    for task in result.results:
        writer.writerow([task.created.isoformat(), task.name, task.status, str(task.value_percent)])

    cursor = _get_cursor(result.next_)
    if cursor:
        print(f"next_token,{cursor}")


def _render_json(ctx, result):
    obj = result.to_dict()
    ret = {"next_token": _get_cursor(result.next_), "results": obj["results"]}
    print(json.dumps(ret, indent=2))


def _get_cursor(url):
    if url:
        qs = urlparse(url).query
        query = parse_qs(qs)
        return query["cursor"][0]
