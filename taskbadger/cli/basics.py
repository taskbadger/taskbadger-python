import csv
import json
import sys
from enum import Enum
from typing import Tuple
from urllib.parse import parse_qs, urlparse

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from taskbadger import StatusEnum, create_task, update_task
from taskbadger.cli.utils import configure_api, err_console, get_actions, get_metadata
from taskbadger.sdk import list_tasks


def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., show_default=False, help="The task name."),
    monitor_id: str = typer.Option(None, help="Associate this task with a monitor."),
    action_def: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help="Action definition e.g. 'success,error email to:me@email.com'",
    ),
    status: StatusEnum = typer.Option(StatusEnum.PROCESSING, help="The initial status of the task."),
    value_max: int = typer.Option(100, help="The maximum value for the task."),
    metadata: list[str] = typer.Option(
        None,
        show_default=False,
        help="Metadata 'key=value' pair to associate with the task. Can be specified multiple times.",
    ),
    metadata_json: str = typer.Option(
        None, show_default=False, help="Metadata to associate with the task. Must be valid JSON."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output. Only the Task ID."),
):
    """Create a task."""
    configure_api(ctx)
    actions = get_actions(action_def)
    metadata = get_metadata(metadata, metadata_json)

    try:
        task = create_task(
            name,
            status=status,
            value_max=value_max,
            data=metadata,
            actions=actions,
            monitor_id=monitor_id,
        )
    except Exception as e:
        err_console.print(f"Error creating task: {e}")
    else:
        if quiet:
            print(task.id)
        else:
            print(f"Task created: {task.public_url}")


def update(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., show_default=False, help="The ID of the task to update."),
    name: str = typer.Option(None, show_default=False, help="Update the name of the task."),
    action_def: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help="Action definition e.g. 'success,error email to:me@email.com'",
    ),
    status: StatusEnum = typer.Option(StatusEnum.PROCESSING, help="The status of the task."),
    value: int = typer.Option(None, show_default=False, help="The current task value (progress)."),
    value_max: int = typer.Option(None, show_default=False, help="The maximum value for the task."),
    metadata: list[str] = typer.Option(
        None,
        show_default=False,
        help="Metadata 'key=value' pair to associate with the task. Can be specified multiple times.",
    ),
    metadata_json: str = typer.Option(
        None, show_default=False, help="Metadata to associate with the task. Must be valid JSON."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="No output."),
):
    """Update a task."""
    configure_api(ctx)
    actions = get_actions(action_def)
    metadata = get_metadata(metadata, metadata_json)

    try:
        task = update_task(
            task_id,
            name=name,
            status=status,
            value=value,
            value_max=value_max,
            data=metadata,
            actions=actions,
        )
    except Exception as e:
        err_console.print(f"Error creating task: {e}")
    else:
        if not quiet:
            print(f"Task updated: {task.public_url}")


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
