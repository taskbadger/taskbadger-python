from collections.abc import Mapping
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatchedActionRequest")


@_attrs_define
class PatchedActionRequest:
    """
    Attributes:
        trigger (Union[Unset, str]):
        integration (Union[Unset, str]):
        config (Union[Unset, Any]):
    """

    trigger: Union[Unset, str] = UNSET
    integration: Union[Unset, str] = UNSET
    config: Union[Unset, Any] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        trigger = self.trigger

        integration = self.integration

        config = self.config

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if trigger is not UNSET:
            field_dict["trigger"] = trigger
        if integration is not UNSET:
            field_dict["integration"] = integration
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        trigger = d.pop("trigger", UNSET)

        integration = d.pop("integration", UNSET)

        config = d.pop("config", UNSET)

        patched_action_request = cls(
            trigger=trigger,
            integration=integration,
            config=config,
        )

        patched_action_request.additional_properties = d
        return patched_action_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
