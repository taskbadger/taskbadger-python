import csv
import json
import sys
from typing import Tuple

import typer
from rich import print

from taskbadger import StatusEnum, create_task, get_task, update_task
from taskbadger.cli.utils import (
    OutputFormat,
    configure_api,
    err_console,
    get_actions,
    get_metadata,
)


def get(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., show_default=False, help="The ID of the task."),
    output_format: OutputFormat = typer.Option(
        OutputFormat.pretty, "--format", "-f", help="Output format"
    ),
):
    """Get a task."""
    configure_api(ctx)
    task = get_task(task_id)
    if output_format == OutputFormat.pretty:
        print(f"Task ID: {task.id}")
        print(f"Created: {task.created.isoformat()}")
        print(f"Name: {task.name}")
        print(f"Status: {task.status}")
        print(f"Percent: {task.value_percent}%")
    elif output_format == OutputFormat.json:
        print(json.dumps(task.to_dict(), indent=2))
    elif output_format == OutputFormat.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow("Task ID,Created,Name,Status,Percent".split(","))
        writer.writerow(
            [
                task.id,
                task.created.isoformat(),
                task.name,
                task.status,
                str(task.value_percent),
            ]
        )


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
    status: StatusEnum = typer.Option(
        StatusEnum.PROCESSING, help="The initial status of the task."
    ),
    value_max: int = typer.Option(100, help="The maximum value for the task."),
    metadata: list[str] = typer.Option(
        None,
        show_default=False,
        help="Metadata 'key=value' pair to associate with the task. Can be specified multiple times.",
    ),
    metadata_json: str = typer.Option(
        None,
        show_default=False,
        help="Metadata to associate with the task. Must be valid JSON.",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Minimal output. Only the Task ID."
    ),
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
    task_id: str = typer.Argument(
        ..., show_default=False, help="The ID of the task to update."
    ),
    name: str = typer.Option(
        None, show_default=False, help="Update the name of the task."
    ),
    action_def: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help="Action definition e.g. 'success,error email to:me@email.com'",
    ),
    status: StatusEnum = typer.Option(
        StatusEnum.PROCESSING, help="The status of the task."
    ),
    value: int = typer.Option(
        None, show_default=False, help="The current task value (progress)."
    ),
    value_max: int = typer.Option(
        None, show_default=False, help="The maximum value for the task."
    ),
    metadata: list[str] = typer.Option(
        None,
        show_default=False,
        help="Metadata 'key=value' pair to associate with the task. Can be specified multiple times.",
    ),
    metadata_json: str = typer.Option(
        None,
        show_default=False,
        help="Metadata to associate with the task. Must be valid JSON.",
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
