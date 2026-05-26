import pytest

from taskbadger._integrations import task_cache
from taskbadger.mug import Badger, Settings


@pytest.fixture(autouse=True)
def _clear_task_cache():
    """Clear the shared integrations task cache around every test so cached
    entries from earlier tests can't leak into later ones."""
    task_cache.cache.clear()
    yield
    task_cache.cache.clear()


@pytest.fixture
def _bind_settings():
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
