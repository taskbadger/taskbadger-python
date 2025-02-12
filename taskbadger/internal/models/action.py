import datetime
from typing import Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="Action")


@_attrs_define
class Action:
    """
    Attributes:
        id (int):
        task (str):
        trigger (str):
        integration (str):
        status (str):
        created (datetime.datetime):
        updated (datetime.datetime):
        config (Union[Unset, Any]):
    """

    id: int
    task: str
    trigger: str
    integration: str
    status: str
    created: datetime.datetime
    updated: datetime.datetime
    config: Union[Unset, Any] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        task = self.task

        trigger = self.trigger

        integration = self.integration

        status = self.status

        created = self.created.isoformat()

        updated = self.updated.isoformat()

        config = self.config

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "task": task,
                "trigger": trigger,
                "integration": integration,
                "status": status,
                "created": created,
                "updated": updated,
            }
        )
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        task = d.pop("task")

        trigger = d.pop("trigger")

        integration = d.pop("integration")

        status = d.pop("status")

        created = isoparse(d.pop("created"))

        updated = isoparse(d.pop("updated"))

        config = d.pop("config", UNSET)

        action = cls(
            id=id,
            task=task,
            trigger=trigger,
            integration=integration,
            status=status,
            created=created,
            updated=updated,
            config=config,
        )

        action.additional_properties = d
        return action

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
