import sys
from unittest import mock

from taskbadger.context_providers.sentry import SentryContextProvider


def test_sentry_provider_not_installed():
    provider = SentryContextProvider()
    with mock.patch.dict(sys.modules, {"sentry_sdk": None}):
        assert provider.snapshot() is None
        assert provider.capture_error_context(ValueError("boom")) is None


def test_sentry_provider_no_event_id():
    provider = SentryContextProvider()
    with mock.patch("sentry_sdk.last_event_id", return_value=None):
        assert provider.capture_error_context(ValueError("boom")) is None


def test_sentry_provider_stale_event_id_not_reported():
    """If last_event_id() hasn't changed since the snapshot, the exception
    was never actually captured by Sentry -- don't report the stale id."""
    provider = SentryContextProvider()
    with mock.patch("sentry_sdk.last_event_id", return_value="stale123"):
        snapshot = provider.snapshot()
        context = provider.capture_error_context(ValueError("boom"), snapshot)
    assert context is None


def test_sentry_provider_event_id_only():
    provider = SentryContextProvider()
    snapshot = None
    with mock.patch("sentry_sdk.last_event_id", return_value="abc123"):
        context = provider.capture_error_context(ValueError("boom"), snapshot)
    assert context == {"event_id": "abc123"}


def test_sentry_provider_with_url():
    provider = SentryContextProvider(organization_slug="acme")
    with mock.patch("sentry_sdk.last_event_id", return_value="abc123"):
        context = provider.capture_error_context(ValueError("boom"))
    assert context == {
        "event_id": "abc123",
        "url": "https://sentry.io/organizations/acme/issues/?query=abc123",
    }


def test_sentry_provider_custom_base_url():
    provider = SentryContextProvider(organization_slug="acme", base_url="https://sentry.example.com/")
    with mock.patch("sentry_sdk.last_event_id", return_value="abc123"):
        context = provider.capture_error_context(ValueError("boom"))
    assert context["url"] == "https://sentry.example.com/organizations/acme/issues/?query=abc123"
