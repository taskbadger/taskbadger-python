import dataclasses

from _contextvars import ContextVar

from taskbadger.internal import AuthenticatedClient

_local = ContextVar("taskbadger_client")


@dataclasses.dataclass
class Settings:
    base_url: str
    token: str
    organization_slug: str
    project_slug: str

    def get_client(self):
        return AuthenticatedClient(self.base_url, self.token)

    def as_kwargs(self):
        return {
            "organization_slug": self.organization_slug,
            "project_slug": self.project_slug,
        }


class Session:
    def __init__(self):
        self._session = None

    def __enter__(self) -> AuthenticatedClient:
        self._session = Badger.current.session()
        return self._session.__enter__()

    def __exit__(self, *args, **kwargs):
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


class MugMeta(type):
    @property
    def current(cls):
        mug = _local.get(None)
        if mug is None:
            mug = Badger(GLOBAL_MUG)
            _local.set(mug)
        return mug


class Badger(metaclass=MugMeta):
    def __init__(self, settings_or_mug=None):
        if isinstance(settings_or_mug, Badger):
            self.settings = settings_or_mug.settings
        else:
            self.settings = settings_or_mug

        self._session = ReentrantSession()

    def bind(self, settings):
        self.settings = settings

    def session(self) -> ReentrantSession:
        return self._session

    def client(self) -> AuthenticatedClient:
        return self.settings.get_client()

    @classmethod
    def is_configured(cls):
        return cls.current.settings is not None


GLOBAL_MUG = Badger()
_local.set(GLOBAL_MUG)
