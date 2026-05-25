"""TaskBadger integration for the Procrastinate task queue.

This module is opt-in. Users install Procrastinate themselves (or via the
``taskbadger[procrastinate]`` extra) and import from here.

Public API:
    - ``track``: decorator to opt a single task into TaskBadger tracking.
    - ``current_task()``: accessor for the TaskBadger task associated with the
      currently-running Procrastinate job (returns ``None`` if not tracked).
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

from .internal.models import StatusEnum

log = logging.getLogger("taskbadger")

# Reserved key used to smuggle the TaskBadger task id through Procrastinate's
# task_kwargs from the deferring process to the worker. Stripped before the
# user function is called.
TB_TASK_ID_KWARG = "__taskbadger_task_id__"

TERMINAL_STATES = {
    StatusEnum.SUCCESS,
    StatusEnum.ERROR,
    StatusEnum.CANCELLED,
    StatusEnum.STALE,
}

# Sentinel attribute names set on a Procrastinate Task object once it has been
# instrumented. Used to make instrumentation idempotent.
_INSTRUMENTED_ATTR = "_taskbadger_instrumented"
_MANUAL_ATTR = "_taskbadger_manual"
_OPTS_ATTR = "_taskbadger_opts"

_current_tb_task_id: ContextVar[str | None] = ContextVar("_current_tb_task_id", default=None)
