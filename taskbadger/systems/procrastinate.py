"""ProcrastinateSystemIntegration — auto-track tasks on a Procrastinate App."""

from __future__ import annotations

from taskbadger._integrations import BaseSystemIntegration
from taskbadger.procrastinate import _instrument_task, _patch_app_task


class ProcrastinateSystemIntegration(BaseSystemIntegration):
    identifier = "procrastinate"

    def __init__(
        self,
        app,
        auto_track_tasks=True,
        includes=None,
        excludes=None,
        record_task_args=False,
    ):
        """
        Args:
            app: The ``procrastinate.App`` instance to instrument.
            auto_track_tasks: Track all tasks regardless of whether they use
                the ``@taskbadger.procrastinate.track`` decorator.
            includes: List of task names to include in auto-tracking. Each
                entry can be a full name or a regex (matched with
                ``re.fullmatch``).
            excludes: List of task names to exclude. Same semantics as
                ``includes``. Exclusions take precedence.
            record_task_args: Record the task's defer kwargs into the
                TaskBadger task's ``data`` under ``procrastinate_task_kwargs``.
        """
        super().__init__(
            auto_track_tasks=auto_track_tasks,
            includes=includes,
            excludes=excludes,
            record_task_args=record_task_args,
        )
        self.app = app

        for task in list(app.tasks.values()):
            _instrument_task(task, system=self)
        _patch_app_task(app, system=self)

    def track_task(self, task_name):
        # Never auto-track Procrastinate's built-in housekeeping tasks
        # (e.g. ``builtin:procrastinate.builtin_tasks.remove_old_jobs``).
        if task_name.startswith("builtin:") or task_name.startswith("procrastinate."):
            return False
        return super().track_task(task_name)
