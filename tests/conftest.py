import pytest

from taskbadger.mug import Badger, Settings


@pytest.fixture
def bind_settings():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))
    yield
    Badger.current.bind(None)
