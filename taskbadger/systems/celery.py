from taskbadger.systems import System


class CelerySystemIntegration(System):
    identifier = "celery"

    def __init__(self, auto_track_tasks=True):
        """
        Args:
            auto_track_tasks: Automatically track all Celery tasks regardless of whether they are using the
                `taskbadger.celery.Task` base class.
        """
        self.auto_track_tasks = auto_track_tasks
        if auto_track_tasks:
            # Importing this here ensures that the Celery signal handlers are registered
            import taskbadger.celery  # noqa
