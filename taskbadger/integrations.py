import dataclasses
from typing import Any

from taskbadger.exceptions import TaskbadgerException
from taskbadger.internal.models import ActionRequest


def from_config(integration_id: str, config: str):
    cls = integration_from_id(integration_id)
    return cls.from_config_string(integration_id, config)


class Integration:
    type: str
    id: str

    def __post_init__(self):
        if not self.id.startswith(self.type):
            raise TaskbadgerException(f"Expected integration ID '{self.id}' to start with '{self.type}'")

    def request_config(self):
        raise NotImplementedError

    @classmethod
    def from_config_string(cls, integration_id, config):
        kwargs = {"id": integration_id}
        if config:
            # convert config string to dict
            # "to:me@me.com,from:you@you.com"
            split_ = [tuple(item.split(":", 1)) for item in config.split(",")]
            kwargs.update(dict(split_))
        return cls(**kwargs)


@dataclasses.dataclass
class Action:
    trigger: str
    integration: Integration

    def to_dict(self) -> dict[str, Any]:
        return ActionRequest(self.trigger, self.integration.id, self.integration.request_config()).to_dict()


@dataclasses.dataclass
class EmailIntegration(Integration):
    type = "email"
    to: str  # custom type
    id: str = "email"

    def request_config(self) -> dict:
        return {"to": self.to}


@dataclasses.dataclass
class WebhookIntegration(Integration):
    type = "webhook"
    id: str

    def request_config(self) -> dict:
        return {}


ALL = [EmailIntegration, WebhookIntegration]
BY_TYPE = {cls.type: cls for cls in ALL}


def integration_from_id(integration_id):
    type_, _ = get_type_id(integration_id)
    try:
        return BY_TYPE[type_]
    except KeyError:
        raise TaskbadgerException(f"Unknown integration type: '{type_}'")


def get_type_id(integration_id: str):
    if ":" in integration_id:
        return integration_id.split(":", 1)
    return integration_id, None
