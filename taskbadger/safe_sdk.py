import logging
from typing import Optional

from .sdk import Mug, create_task, update_task

log = logging.getLogger("taskbadger")


def create_task_safe(name: str, **kwargs) -> Optional[str]:
    """Create a Task.

    Arguments:
        name: The name of the task.
        **kwargs: See ``taskbadger.create_task``

    Returns:
        Task ID
    """
    if not Mug.is_configured:
        return None

    try:
        task = create_task(name, **kwargs)
    except Exception:
        log.exception("Error creating task '%s'", name)
    else:
        return task.id


def update_task_safe(task_id: str, **kwargs) -> None:
    """Update a task.
    Requires only the task ID and fields to update.

    Arguments:
        task_id: The ID of the task to update.
        **kwargs: See ``taskbadger.update_task``
    """
    if not Mug.is_configured:
        return

    try:
        update_task(task_id, **kwargs)
    except Exception:
        log.exception("Error updating task '%s'", task_id)
