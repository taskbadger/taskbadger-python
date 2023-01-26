import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

import attr
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.action_config import ActionConfig


T = TypeVar("T", bound="Action")


@attr.s(auto_attribs=True)
class Action:
    """
    Attributes:
        trigger (str):
        integration (str):
        id (Union[Unset, int]):
        task (Union[Unset, str]):
        status (Union[Unset, str]):
        config (Union[Unset, ActionConfig]):
        created (Union[Unset, datetime.datetime]):
        updated (Union[Unset, datetime.datetime]):
    """

    trigger: str
    integration: str
    id: Union[Unset, int] = UNSET
    task: Union[Unset, str] = UNSET
    status: Union[Unset, str] = UNSET
    config: Union[Unset, "ActionConfig"] = UNSET
    created: Union[Unset, datetime.datetime] = UNSET
    updated: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        trigger = self.trigger
        integration = self.integration
        id = self.id
        task = self.task
        status = self.status
        config: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.config, Unset):
            config = self.config.to_dict()

        created: Union[Unset, str] = UNSET
        if not isinstance(self.created, Unset):
            created = self.created.isoformat()

        updated: Union[Unset, str] = UNSET
        if not isinstance(self.updated, Unset):
            updated = self.updated.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "trigger": trigger,
                "integration": integration,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if task is not UNSET:
            field_dict["task"] = task
        if status is not UNSET:
            field_dict["status"] = status
        if config is not UNSET:
            field_dict["config"] = config
        if created is not UNSET:
            field_dict["created"] = created
        if updated is not UNSET:
            field_dict["updated"] = updated

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.action_config import ActionConfig

        d = src_dict.copy()
        trigger = d.pop("trigger")

        integration = d.pop("integration")

        id = d.pop("id", UNSET)

        task = d.pop("task", UNSET)

        status = d.pop("status", UNSET)

        _config = d.pop("config", UNSET)
        config: Union[Unset, ActionConfig]
        if isinstance(_config, Unset):
            config = UNSET
        else:
            config = ActionConfig.from_dict(_config)

        _created = d.pop("created", UNSET)
        created: Union[Unset, datetime.datetime]
        if isinstance(_created, Unset):
            created = UNSET
        else:
            created = isoparse(_created)

        _updated = d.pop("updated", UNSET)
        updated: Union[Unset, datetime.datetime]
        if isinstance(_updated, Unset):
            updated = UNSET
        else:
            updated = isoparse(_updated)

        action = cls(
            trigger=trigger,
            integration=integration,
            id=id,
            task=task,
            status=status,
            config=config,
            created=created,
            updated=updated,
        )

        action.additional_properties = d
        return action

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
