import dataclasses
from enum import Enum
from typing import Any, Dict, Generator, List, Tuple

from taskbadger.internal.models import ActionRequest, ActionRequestConfig


class Integrations(str, Enum):
    email = "email"


def from_config(integration: Integrations, config: str):
    if integration == Integrations.email:
        split_ = [tuple(item.split(":", 1)) for item in config.split(",")]
        kwargs = dict(split_)
        return EmailIntegration(**kwargs)


class Integration:
    name: str

    def request_config(self):
        raise NotImplementedError


@dataclasses.dataclass
class Action:
    trigger: str
    integration: Integration

    def to_dict(self) -> Dict[str, Any]:
        return ActionRequest(self.trigger, self.integration.name, self.integration.request_config()).to_dict()


@dataclasses.dataclass
class EmailIntegration(Integration):
    name = "email"
    to: str  # custom type

    def request_config(self) -> ActionRequestConfig:
        return ActionRequestConfig.from_dict({"to": self.to})
