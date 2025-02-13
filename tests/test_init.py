import pytest

from taskbadger import Badger, init
from taskbadger.exceptions import ConfigurationError
from taskbadger.mug import _local


@pytest.fixture(autouse=True)
def _reset():
    _local.set(Badger())


def test_init():
    init("org", "project", "token", before_create=lambda x: x)


def test_init_import_before_create():
    init("org", "project", "token", before_create="tests.test_init._before_create")


def test_init_import_before_create_fail():
    with pytest.raises(ConfigurationError):
        init("org", "project", "token", before_create="missing")


def _before_create(_):
    pass
