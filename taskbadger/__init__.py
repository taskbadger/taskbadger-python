from .decorators import track
from .integrations import Action, EmailIntegration, WebhookIntegration
from .internal.models import StatusEnum
from .mug import Badger, Session
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import DefaultMergeStrategy, Task, create_task, get_task, init, update_task

__all__ = [
    "track",
    "Action",
    "EmailIntegration",
    "WebhookIntegration",
    "StatusEnum",
    "Badger",
    "Session",
    "create_task_safe",
    "update_task_safe",
    "DefaultMergeStrategy",
    "Task",
    "create_task",
    "get_task",
    "init",
    "update_task",
]

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "dev"


def current_scope():
    return Badger.current.scope()
