from unittest import mock

import pytest

from taskbadger._error_context import capture_error_data, reset_error_context, start_error_context
from taskbadger.context_providers import ContextProvider
from taskbadger.mug import Badger, Settings


@pytest.fixture
def bind_settings_with_providers():
    def _bind(providers):
        Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj", context_providers=providers))

    yield _bind
    Badger.current.bind(None)


def test_capture_error_data_no_providers():
    assert capture_error_data(ValueError("boom")) == {"exception": "boom"}


def test_capture_error_data_message_override():
    data = capture_error_data(ValueError("boom"), message="custom message")
    assert data == {"exception": "custom message"}


def test_capture_error_data_not_configured():
    Badger.current.bind(None)
    assert capture_error_data(ValueError("boom")) == {"exception": "boom"}


def test_capture_error_data_with_provider(bind_settings_with_providers):
    class FakeProvider(ContextProvider):
        identifier = "fake"

        def capture_error_context(self, exception, snapshot=None):
            return {"detail": str(exception)}

    bind_settings_with_providers([FakeProvider()])

    data = capture_error_data(ValueError("boom"))
    assert data == {"exception": "boom", "fake": {"detail": "boom"}}


def test_capture_error_data_provider_returning_none(bind_settings_with_providers):
    class FakeProvider(ContextProvider):
        identifier = "fake"

        def capture_error_context(self, exception, snapshot=None):
            return None

    bind_settings_with_providers([FakeProvider()])

    assert capture_error_data(ValueError("boom")) == {"exception": "boom"}


def test_capture_error_data_provider_raises(bind_settings_with_providers):
    class BrokenProvider(ContextProvider):
        identifier = "broken"

        def capture_error_context(self, exception, snapshot=None):
            raise RuntimeError("provider failed")

    bind_settings_with_providers([BrokenProvider()])

    with mock.patch("taskbadger._error_context.log") as log:
        data = capture_error_data(ValueError("boom"))
    assert data == {"exception": "boom"}
    log.warning.assert_called_once()


def test_capture_error_data_uses_snapshot_from_start_error_context(bind_settings_with_providers):
    """A provider that only reports a fresh capture (comparing against its
    snapshot) should see the snapshot taken by start_error_context."""

    calls = []

    class TrackingProvider(ContextProvider):
        identifier = "tracking"

        def snapshot(self):
            return "baseline"

        def capture_error_context(self, exception, snapshot=None):
            calls.append(snapshot)
            return None if snapshot == "baseline" else {"unexpected": True}

    bind_settings_with_providers([TrackingProvider()])

    token = start_error_context()
    try:
        capture_error_data(ValueError("boom"))
    finally:
        reset_error_context(token)

    assert calls == ["baseline"]


def test_capture_error_data_without_snapshot_passes_none(bind_settings_with_providers):
    class FakeProvider(ContextProvider):
        identifier = "fake"

        def capture_error_context(self, exception, snapshot=None):
            return {"snapshot": snapshot}

    bind_settings_with_providers([FakeProvider()])

    data = capture_error_data(ValueError("boom"))
    assert data["fake"] == {"snapshot": None}
