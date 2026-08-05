from taskbadger.context_providers import ContextProvider


class SentryContextProvider(ContextProvider):
    """Links a failed task to the corresponding Sentry issue.

    Reads back `sentry_sdk.last_event_id()` rather than capturing the exception
    itself, on the assumption the surrounding system already reports its own
    exceptions to Sentry (e.g. via a framework integration). To avoid linking to
    a stale event left over from something unrelated, a snapshot is taken when
    the task starts and the event id is only reported if it changed by the time
    the task errors.

    Requires the `sentry-sdk` package; a no-op if it isn't installed.
    """

    identifier = "sentry"

    def __init__(self, organization_slug: str = None, base_url: str = "https://sentry.io"):
        self.organization_slug = organization_slug
        self.base_url = base_url.rstrip("/")

    def snapshot(self):
        try:
            import sentry_sdk
        except ImportError:
            return None
        return sentry_sdk.last_event_id()

    def capture_error_context(self, exception: BaseException, snapshot=None) -> dict | None:
        try:
            import sentry_sdk
        except ImportError:
            return None

        event_id = sentry_sdk.last_event_id()
        if not event_id or event_id == snapshot:
            return None

        context = {"event_id": event_id}
        if self.organization_slug:
            context["url"] = f"{self.base_url}/organizations/{self.organization_slug}/issues/?query={event_id}"
        return context
