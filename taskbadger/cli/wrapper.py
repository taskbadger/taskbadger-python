import typer
from rich import print

from taskbadger import DefaultMergeStrategy, Session, StatusEnum, Task
from taskbadger.cli.utils import configure_api, err_console, get_actions, merge_kv_json
from taskbadger.process import ProcessRunner


def run(
    ctx: typer.Context,
    name: str = typer.Argument(..., show_default=False, help="The task name"),
    monitor_id: str = typer.Option(None, help="Associate this task with a monitor."),
    update_frequency: int = typer.Option(5, metavar="SECONDS", min=5, max=300, help="Seconds between updates."),
    action_def: tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--action",
        "-a",
        metavar="<trigger integration config>",
        show_default=False,
        help="Action definition e.g. 'success,error email to:me@email.com'",
    ),
    tag: list[str] = typer.Option(
        None,
        show_default=False,
        help="Tags: 'name=value' pair to associate with the task. Can be specified multiple times.",
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
    configure_api(ctx)
    actions = get_actions(action_def)
    tags = merge_kv_json(tag, "")
    stale_timeout = update_frequency * 2
    with Session():
        try:
            task = Task.create(
                name,
                status=StatusEnum.PROCESSING,
                stale_timeout=stale_timeout,
                actions=actions,
                monitor_id=monitor_id,
                tags=tags,
            )
        except Exception as e:
            err_console.print(f"Error creating task: {e}")
            task = None
        else:
            print(f"Task created: {task.public_url}")
        env = {"TASKBADGER_TASK_ID": task.id} if task else None
        try:
            process = ProcessRunner(
                ctx.args,
                env,
                capture_output=capture_output,
                update_frequency=update_frequency,
            )
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
