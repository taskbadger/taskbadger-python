from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

import attr

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.action_request_config import ActionRequestConfig


T = TypeVar("T", bound="ActionRequest")


@attr.s(auto_attribs=True)
class ActionRequest:
    """
    Attributes:
        trigger (str):
        integration (str):
        config (Union[Unset, ActionRequestConfig]):
    """

    trigger: str
    integration: str
    config: Union[Unset, "ActionRequestConfig"] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        trigger = self.trigger
        integration = self.integration
        config: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.config, Unset):
            config = self.config.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "trigger": trigger,
                "integration": integration,
            }
        )
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.action_request_config import ActionRequestConfig

        d = src_dict.copy()
        trigger = d.pop("trigger")

        integration = d.pop("integration")

        _config = d.pop("config", UNSET)
        config: Union[Unset, ActionRequestConfig]
        if isinstance(_config, Unset):
            config = UNSET
        else:
            config = ActionRequestConfig.from_dict(_config)

        action_request = cls(
            trigger=trigger,
            integration=integration,
            config=config,
        )

        action_request.additional_properties = d
        return action_request

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
