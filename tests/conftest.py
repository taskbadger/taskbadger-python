import pytest

from taskbadger.mug import Badger, Settings


@pytest.fixture
def bind_settings():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))
    yield
    Badger.current.bind(None)


@pytest.fixture(scope="session", autouse=True)
def celery_config():
    """Test against Redis to ensure serialization works"""
    return {
        "broker_url": "redis://localhost:6379",
        "result_backend": "redis://localhost:6379",
    }
