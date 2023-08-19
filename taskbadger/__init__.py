from .integrations import Action, EmailIntegration, WebhookIntegration
from .internal.models import StatusEnum
from .mug import Session
from .safe_sdk import create_task_safe, update_task_safe
from .sdk import Task, create_task, get_task, init, update_task

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


try:
    __version__ = importlib_metadata.version(__name__)
except importlib_metadata.PackageNotFoundError:
    __version__ = "dev"
