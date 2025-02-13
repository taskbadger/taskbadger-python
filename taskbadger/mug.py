import dataclasses
from contextlib import ContextDecorator
from contextvars import ContextVar
from copy import deepcopy
from typing import Callable, Optional, Union

from taskbadger.internal import AuthenticatedClient
from taskbadger.systems import System

_local = ContextVar("taskbadger_client")


Callback = Union[str, Callable[[dict], Optional[dict]]]


@dataclasses.dataclass
class Settings:
    base_url: str
    token: str
    organization_slug: str
    project_slug: str
    systems: dict[str, System] = dataclasses.field(default_factory=dict)
    before_create: Callback = None

    def get_client(self):
        return AuthenticatedClient(self.base_url, self.token)

    def as_kwargs(self):
        return {
            "organization_slug": self.organization_slug,
            "project_slug": self.project_slug,
        }

    def get_system_by_id(self, identifier: str) -> System:
        return self.systems.get(identifier)

    def __str__(self):
        return (
            f"Settings(base_url='{self.base_url}',"
            f" token='{self.token[:6]}...',"
            f" organization_slug='{self.organization_slug}',"
            f" project_slug='{self.project_slug}')"
        )


class Session(ContextDecorator):
    def __init__(self):
        self._session = None

    def __enter__(self) -> Union[AuthenticatedClient, None]:
        if Badger.is_configured():
            self._session = Badger.current.session()
            return self._session.__enter__()

    def __exit__(self, *args, **kwargs) -> None:
        if self._session:
            sess = self._session
            self._session = None
            sess.__exit__(*args, **kwargs)


class ReentrantSession:
    def __init__(self):
        self.client = None
        self.stack = []

    def __enter__(self) -> AuthenticatedClient:
        if not self.client:
            self.client = Badger.current.client()
            self.client.__enter__()
        self.stack.append(True)
        return self.client

    def __exit__(self, *args, **kwargs):
        self.stack.pop()
        if not self.stack:
            self.client.__exit__(*args, **kwargs)
            self.client = None


class Scope:
    """Scope holds global data which will be added to every task created within the current scope.

    Scope data will be merged with task data when creating a task where data provided directly to the task
    will override scope data.
    """

    def __init__(self):
        self.stack = []
        self.context = {}
        self.tags = {}

    def __enter__(self):
        self.stack.append((self.context, self.tags))
        self.context = deepcopy(self.context)
        self.tags = deepcopy(self.tags)
        return self

    def __exit__(self, *args):
        self.context, self.tags = self.stack.pop()

    def __setitem__(self, key, value):
        self.context[key] = value

    def tag(self, tags: dict[str, str]):
        self.tags.update(tags)


class MugMeta(type):
    @property
    def current(cls):
        # Note that changes in the parent thread are not propagated to child threads
        # i.e. if this is called in a child thread before configuration is set in the parent thread
        # the config will not propagate to the child thread.
        mug = _local.get(None)
        if mug is None:
            mug = Badger(GLOBAL_MUG)
            _local.set(mug)
        return mug


class Badger(metaclass=MugMeta):
    def __init__(self, settings_or_mug=None):
        self._session = ReentrantSession()
        self._scope = Scope()

        if isinstance(settings_or_mug, Badger):
            self.settings = settings_or_mug.settings
            self._scope.context = deepcopy(settings_or_mug._scope.context)
            self._scope.tags = deepcopy(settings_or_mug._scope.tags)
        else:
            self.settings = settings_or_mug

    def bind(self, settings, tags=None):
        self.settings = settings
        self._scope.tags = tags or {}

    def session(self) -> ReentrantSession:
        return self._session

    def client(self) -> AuthenticatedClient:
        return self.settings.get_client()

    def scope(self) -> Scope:
        return self._scope

    def call_before_create(self, task: dict) -> Optional[dict]:
        if self.settings and self.settings.before_create:
            return self.settings.before_create(task)
        return task

    @classmethod
    def is_configured(cls):
        return cls.current.settings is not None


GLOBAL_MUG = Badger()
_local.set(GLOBAL_MUG)
