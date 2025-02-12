import datetime
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.action_config import ActionConfig


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
        config (Union[Unset, ActionConfig]):
    """

    id: int
    task: str
    trigger: str
    integration: str
    status: str
    created: datetime.datetime
    updated: datetime.datetime
    config: Union[Unset, "ActionConfig"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        task = self.task

        trigger = self.trigger

        integration = self.integration

        status = self.status

        created = self.created.isoformat()

        updated = self.updated.isoformat()

        config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.config, Unset):
            config = self.config.to_dict()

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
        from ..models.action_config import ActionConfig

        d = src_dict.copy()
        id = d.pop("id")

        task = d.pop("task")

        trigger = d.pop("trigger")

        integration = d.pop("integration")

        status = d.pop("status")

        created = isoparse(d.pop("created"))

        updated = isoparse(d.pop("updated"))

        _config = d.pop("config", UNSET)
        config: Union[Unset, ActionConfig]
        if isinstance(_config, Unset):
            config = UNSET
        else:
            config = ActionConfig.from_dict(_config)

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
