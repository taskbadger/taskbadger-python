from taskbadger._integrations import BaseSystemIntegration


class CelerySystemIntegration(BaseSystemIntegration):
    identifier = "celery"

    def __init__(self, auto_track_tasks=True, includes=None, excludes=None, record_task_args=False):
        """
        Args:
            auto_track_tasks: Automatically track all Celery tasks regardless of whether they are using the
                `taskbadger.celery.Task` base class.
            includes: A list of task names to include in tracking. These can be either the full task name
                (e.g. `myapp.tasks.export_data`) or a regular expression (e.g. `export_.*`). If a task name
                matches both an include and an exclude, it will be excluded.
            excludes: A list of task names to exclude from tracking. As with `includes`, these can be either
                the full task name or a regular expression. Exclusions take precedence over inclusions.
            record_task_args: Record the arguments passed to each task.
        """
        super().__init__(
            auto_track_tasks=auto_track_tasks,
            includes=includes,
            excludes=excludes,
            record_task_args=record_task_args,
        )

        if auto_track_tasks:
            # Importing this here ensures that the Celery signal handlers are registered
            import taskbadger.celery  # noqa: F401
