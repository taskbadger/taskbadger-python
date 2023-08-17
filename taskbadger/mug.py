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

    def bind(self, settings):
        self.settings = settings

    def client(self) -> AuthenticatedClient:
        return self.settings.get_client()

    def is_configured(self):
        return self.settings is not None


GLOBAL_MUG = Badger()
_local.set(GLOBAL_MUG)
