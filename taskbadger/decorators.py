from functools import wraps

from .safe_sdk import create_task_safe, update_task_safe
from .sdk import StatusEnum


def track(func=None, *, name=None, monitor_id=None, max_runtime=None):
    """
    Decorator to track a function as a task.

    Usage:
    ```
    import taskbadger

    @app.task
    @taskbadger.track
    def test(arg):
        print(arg)
    ```

    Arguments:
        name: The name of the task. Defaults to the function name.
        monitor_id: The ID of the monitor to associate the task with.
        max_runtime: The maximum runtime of the task in seconds. If the task takes longer than this,
                     it will be marked as an error.

    If you use this with celery, put the `@taskbadger.track` decorator below Celery's `@app.task` decorator.
    """

    def _decorator(func):
        if not callable(func):
            raise Exception(f"Function must be callable: {func!r}")

        task_name = name or func.__name__

        @wraps(func)
        def _inner(*args, **kwargs):
            task_id = create_task_safe(
                task_name, status=StatusEnum.PROCESSING, max_runtime=max_runtime, monitor_id=monitor_id
            )
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                task_id and update_task_safe(task_id, status=StatusEnum.ERROR, data={"exception": str(e)})
                raise

            task_id and update_task_safe(task_id, status=StatusEnum.SUCCESS)
            return result

        return _inner

    return _decorator if func is None else _decorator(func)
