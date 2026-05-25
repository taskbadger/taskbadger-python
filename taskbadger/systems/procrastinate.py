"""ProcrastinateSystemIntegration — auto-track tasks on a Procrastinate App."""

from __future__ import annotations

import re

from taskbadger.procrastinate import _instrument_task, _patch_app_task
from taskbadger.systems import System


class ProcrastinateSystemIntegration(System):
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
        self.app = app
        self.auto_track_tasks = auto_track_tasks
        self.includes = includes
        self.excludes = excludes
        self.record_task_args = record_task_args

        for task in list(app.tasks.values()):
            _instrument_task(task, system=self)
        _patch_app_task(app, system=self)

    def track_task(self, task_name):
        if not self.auto_track_tasks:
            return False

        if self.excludes:
            for exclude in self.excludes:
                if re.fullmatch(exclude, task_name):
                    return False

        if self.includes:
            for include in self.includes:
                if re.fullmatch(include, task_name):
                    break
            else:
                return False

        return True
