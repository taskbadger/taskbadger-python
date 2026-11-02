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

# (id of the running task, id of its parent or None if it is a root task,
#  id of the first attempt if the running task is a retry, else None)
_current: ContextVar[tuple[str, str | None, str | None] | None] = ContextVar("taskbadger_current_task", default=None)


def enter_task(task_id: str, parent: str = None, retry_of: str = None):
    """Mark `task_id` as the task running in this context.

    Arguments:
        task_id: The running task.
        parent: The running task's own parent, if it has one.
        retry_of: The first attempt, if the running task is itself a retry.

    Returns:
        A token to pass to `exit_task`.
    """
    return _current.set((task_id, parent, retry_of))


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


def retry_of_id() -> str | None:
    """The id to use as `retry_of` for a retry of the task running right now.

    The first attempt: the running task itself, or the task it is a retry of. Retries all point at
    the first attempt, so the API can count them per task. `None` outside a tracked task. The
    retry's `parent` is still `parent_id()`: under the first attempt for a top-level task,
    alongside it for a child.
    """
    current = _current.get()
    if current is None:
        return None
    task_id, _, retry_of = current
    return retry_of or task_id
