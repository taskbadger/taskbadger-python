class ContextProvider:
    """Base class for pluggable providers that attach extra context to a task's
    ``data`` when it errors, e.g. so the TaskBadger UI can link out to an
    external system (Sentry, Rollbar, etc.).

    Registered via `init(context_providers=[...])` and consulted whenever a
    tracked task (via `@track`, the Celery/Procrastinate integrations) errors.

    Implementations that read back state some other system captured on its own
    (rather than capturing it themselves, which risks duplicate reporting)
    should override `snapshot` to record a baseline when the task starts, so
    `capture_error_context` can tell a fresh capture from a stale one left
    over from something unrelated.
    """

    identifier: str = None

    def snapshot(self):
        """Called when a tracked task starts, before user code runs. Return an
        opaque value to be passed back as *snapshot* to `capture_error_context`.
        Default: `None` (no baseline tracking).
        """
        return None

    def capture_error_context(self, exception: BaseException, snapshot=None) -> dict | None:
        """Return extra context for *exception*, or `None` if there is nothing
        to add. The result is stored under `data[self.identifier]`.

        *snapshot* is whatever this provider's `snapshot()` returned when the
        task started.
        """
        raise NotImplementedError
