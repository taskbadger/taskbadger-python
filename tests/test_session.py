import random
import threading
import time

import pytest

from taskbadger.mug import GLOBAL_MUG, Badger, Session, Settings


@pytest.fixture(autouse=True)
def bind_settings():
    Badger.current.bind(Settings("https://taskbadger.net", "token", "org", "proj"))


def test_session_singleton():
    assert Badger.current == GLOBAL_MUG
    session = Badger.current.session()
    assert session.client is None
    assert session.stack == []
    assert session == Badger.current.session()


def test_session_global():
    session = Session()
    with session as client:
        assert Badger.current.session().client is client
    assert session._session is None


def test_session_reentrant():
    session = Badger.current.session()
    assert session.client is None
    assert session.stack == []
    with session:
        client = session.client
        assert client is not None
        assert session.stack == [True]
        with session:
            assert session.client is client
            assert session.stack == [True, True]
        assert session.client is client
        assert session.stack == [True]
    assert session.client is None
    assert session.stack == []


def test_session_multiple_threads():
    """Test that each thread gets its own session."""
    num_tasks = 10
    threads = []
    clients = []
    barrier = threading.Barrier(num_tasks, timeout=5)

    for i in range(num_tasks):
        t = TestThread(f"<thread {i}>", barrier, clients)
        threads.append(t)
        t.start()

    loopcount = 0
    max_loops = len(threads) * 2
    while len(threads):
        threads[0].join(1)
        if not threads[0].is_alive():
            threads.pop(0)
        loopcount += 1
        if loopcount > max_loops:
            pytest.fail("Threads did not complete")

    assert len(clients) == num_tasks
    assert len({id(s) for s in clients}) == 10


class TestThread(threading.Thread):
    __test__ = False

    def __init__(self, name, barrier, clients):
        threading.Thread.__init__(self, name=name)
        self.barrier = barrier
        self.clients = clients

    def run(self):
        delay = random.random() / 10000.0

        self.barrier.wait()
        time.sleep(delay)

        session = Badger.current.session()
        assert session.client is None
        assert session.stack == []
        with session as client:
            assert client is not None
            self.clients.append(client)
