import subprocess
from typing import List

import typer

import taskbadger as tb

app = typer.Typer()

tb.init_from_env()


@app.command()
def monitor(name: str, command: List[str] = typer.Argument(None)):
    task = tb.Task.create(name)
    result = subprocess.run(command, env={"TASKBADGER_TASK_ID": task.id})
    if result.returncode != 0:
        task.success()
    else:
        task.error(data={"return_code": result.returncode})


if __name__ == "__main__":
    app()
