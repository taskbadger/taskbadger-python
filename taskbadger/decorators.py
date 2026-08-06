import logging
from functools import wraps

from ._current_task import enter_task, exit_task, parent_id
from ._error_context import capture_error_data, reset_error_context, start_error_context
from ._integrations import parent_of
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
    **task_kwargs,
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
            create_kwargs = {
                "status": StatusEnum.PROCESSING,
                "max_runtime": max_runtime,
                "monitor_id": monitor_id,
            }
            enclosing_task = parent_id()
            if enclosing_task:
                create_kwargs["parent"] = enclosing_task
            # an explicit `parent` in task_kwargs wins over the enclosing task
            create_kwargs.update(task_kwargs)
            task = create_task_safe(task_name, **create_kwargs)
            token = start_error_context()
            # so that tasks created while `func` runs are nested under this one
            task_token = enter_task(task.id, parent_of(task)) if task else None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                _update_task(
                    task,
                    status=StatusEnum.ERROR,
                    data=capture_error_data(e),
                    data_merge_strategy="default",
                )
                raise
            finally:
                if task_token is not None:
                    exit_task(task_token)
                reset_error_context(token)

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
