"""Tracks which tracked task is running in the current context so that tasks
created while it runs can be attached to it as children. Not part of the public
API.

Task Badger nests tasks a single level deep, so `parent_id` never returns the
id of a task that is itself a child: entering a task that already has a parent
keeps that parent as the id offered for nesting. A task deferred by a child
therefore lands alongside it under the same root rather than being rejected.

Call sites resolve a task's own parent themselves — they all have it to hand
already (from the create response, or from the cache the status update fills),
which keeps this module free of API calls.
"""

from contextvars import ContextVar

# (id of the running task, id of its parent or None if it is a root task, whether it is a retry)
_current: ContextVar[tuple[str, str | None, bool] | None] = ContextVar("taskbadger_current_task", default=None)


def enter_task(task_id: str, parent: str = None, is_retry: bool = False):
    """Mark `task_id` as the task running in this context.

    Arguments:
        task_id: The running task.
        parent: The running task's own parent, if it has one.
        is_retry: Whether the running task is itself a retry of its parent.

    Returns:
        A token to pass to `exit_task`.
    """
    return _current.set((task_id, parent, is_retry))


def exit_task(token) -> None:
    _current.reset(token)


def current_task_id() -> str | None:
    """The id of the tracked task running in this context, if any."""
    current = _current.get()
    return current[0] if current else None


def parent_id() -> str | None:
    """The id a task created right now should use as its `parent`.

    `None` outside a tracked task.
    """
    current = _current.get()
    if current is None:
        return None
    task_id, parent, _ = current
    return parent or task_id


def retry_parent_id() -> str | None:
    """The id to use as `parent` for a retry of the task running right now.

    A retry is nested under the first attempt, so this is the running task for the first attempt
    and the first attempt again when the running task is itself a retry. `None` when there is no
    suitable first attempt: outside a tracked task, or when the running task is a child of some
    other task (a fan-out child), since retries, like children, can't be nested a level deeper.
    The caller should then create the retry as an ordinary task.
    """
    current = _current.get()
    if current is None:
        return None
    task_id, parent, is_retry = current
    if parent is None:
        return task_id
    return parent if is_retry else None
