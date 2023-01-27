import dataclasses

from taskbadger.internal.models import ActionRequest, ActionRequestConfig


class Integration:
    name: str

    def request_config(self):
        raise NotImplementedError


@dataclasses.dataclass
class Action:
    trigger: str
    integration: Integration

    def for_request(self) -> ActionRequest:
        return ActionRequest(self.integration.name, self.trigger, self.integration.request_config())


@dataclasses.dataclass
class EmailIntegration(Integration):
    name = "email"
    to: str  # custom type

    def request_config(self) -> ActionRequestConfig:
        return ActionRequestConfig.from_dict({"to": self.to})
