import dataclasses
from typing import Any, Dict

from taskbadger.internal.models import ActionRequest, ActionRequestConfig


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
