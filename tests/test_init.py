import warnings

import httpx
import pytest

from taskbadger import Badger, init
from taskbadger.exceptions import ConfigurationError
from taskbadger.mug import DEFAULT_HTTP_TIMEOUT, _local


@pytest.fixture(autouse=True)
def _reset():
    b_global = Badger.current
    _local.set(Badger())
    yield
    _local.set(b_global)


def test_init():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        init("org", "project", "token", before_create=lambda x: x)


def test_init_import_before_create():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        init("org", "project", "token", before_create="tests.test_init._before_create")


def test_init_import_before_create_fail():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(ConfigurationError):
            init("org", "project", "token", before_create="missing")


def test_init_default_timeout():
    _init_token()
    assert Badger.current.settings.timeout == DEFAULT_HTTP_TIMEOUT
    assert Badger.current.client().get_httpx_client().timeout == httpx.Timeout(DEFAULT_HTTP_TIMEOUT)


def test_init_timeout_override():
    _init_token(timeout=30)
    assert Badger.current.client().get_httpx_client().timeout == httpx.Timeout(30)


def test_init_timeout_from_env(monkeypatch):
    monkeypatch.setenv("TASKBADGER_HTTP_TIMEOUT", "12.5")
    _init_token()
    assert Badger.current.settings.timeout == 12.5


def test_init_timeout_arg_beats_env(monkeypatch):
    monkeypatch.setenv("TASKBADGER_HTTP_TIMEOUT", "12.5")
    _init_token(timeout=httpx.Timeout(1, connect=2))
    assert Badger.current.client().get_httpx_client().timeout == httpx.Timeout(1, connect=2)


def test_init_timeout_from_env_invalid(monkeypatch):
    monkeypatch.setenv("TASKBADGER_HTTP_TIMEOUT", "soon")
    with pytest.raises(ConfigurationError):
        _init_token()


def _init_token(**kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        init("org", "project", "token", **kwargs)


def _before_create(_):
    pass
