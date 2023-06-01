import dataclasses
from enum import Enum
from typing import Any, Dict

from taskbadger.exceptions import TaskbadgerException
from taskbadger.internal.models import ActionRequest, ActionRequestConfig


class Integrations(str, Enum):
    email = "email"


def from_config(integration: Integrations, config: str):
    if integration == Integrations.email:
        split_ = [tuple(item.split(":", 1)) for item in config.split(",")]
        kwargs = dict(split_)
        return EmailIntegration(**kwargs)


class Integration:
    type: str
    id: str

    def __post_init__(self):
        if not self.id.startswith(self.type):
            raise TaskbadgerException(f"Expected integration ID '{self.id}' to start with '{self.type}'")

    def request_config(self):
        raise NotImplementedError


@dataclasses.dataclass
class Action:
    trigger: str
    integration: Integration

    def to_dict(self) -> Dict[str, Any]:
        return ActionRequest(self.trigger, self.integration.id, self.integration.request_config()).to_dict()


@dataclasses.dataclass
class EmailIntegration(Integration):
    type = "email"
    id = "email"
    to: str  # custom type

    def request_config(self) -> ActionRequestConfig:
        return ActionRequestConfig.from_dict({"to": self.to})


@dataclasses.dataclass
class WebhookIntegration(Integration):
    type = "webhook"
    id: str

    def request_config(self) -> ActionRequestConfig:
        return ActionRequestConfig.from_dict({})
