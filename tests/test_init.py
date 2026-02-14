import warnings

import pytest

from taskbadger import Badger, init
from taskbadger.exceptions import ConfigurationError
from taskbadger.mug import _local


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


def _before_create(_):
    pass
