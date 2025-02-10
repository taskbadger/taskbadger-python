import logging
from functools import wraps

from .mug import Session
from .safe_sdk import create_task_safe
from .sdk import StatusEnum

log = logging.getLogger("taskbadger")


def track(
    func=None,
    *,
    name: str = None,
    monitor_id: str = None,
    max_runtime: int = None,
    **kwargs,
):
    """
    Decorator to track a function as a task.

    Usage:
    ```
    import taskbadger

    @taskbadger.track
    def test(arg):
        print(arg)
    ```

    Arguments:
        name: The name of the task. Defaults to the fully qualified name of the function.
        monitor_id: The ID of the monitor to associate the task with.
        max_runtime: The maximum runtime of the task in seconds. If the task takes longer than this,
                     it will be marked as an error.
        **kwargs: See [taskbadger.create_task][]
    """

    def _decorator(func):
        if not callable(func):
            raise Exception(f"Function must be callable: {func!r}")

        task_name = name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        @Session()
        def _inner(*args, **kwargs):
            task = create_task_safe(
                task_name,
                status=StatusEnum.PROCESSING,
                max_runtime=max_runtime,
                monitor_id=monitor_id,
                **kwargs,
            )
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                _update_task(
                    task,
                    status=StatusEnum.ERROR,
                    data={"exception": str(e)},
                    data_merge_strategy="default",
                )
                raise

            _update_task(task, status=StatusEnum.SUCCESS)
            return result

        return _inner

    return _decorator if func is None else _decorator(func)


def _update_task(task, **kwargs):
    if task:
        _update_safe(task, **kwargs)


def _update_safe(task, **kwargs):
    try:
        task.update(**kwargs)
    except Exception as e:
        log.warning("Error updating task '%s': %s", task.id, e)
