import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

import attr
from dateutil.parser import isoparse

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_data import TaskData


T = TypeVar("T", bound="Task")


@attr.s(auto_attribs=True)
class Task:
    """
    Attributes:
        name (str): Name of the task
        id (Union[Unset, str]): Task ID
        organization (Union[Unset, str]):
        project (Union[Unset, str]):
        status (Union[Unset, StatusEnum]):  Default: StatusEnum.PENDING.
        value (Union[Unset, None, int]): Current progress value
        value_percent (Union[Unset, None, int]):
        data (Union[Unset, None, TaskData]): Custom metadata
        created (Union[Unset, datetime.datetime]):
        updated (Union[Unset, datetime.datetime]):
    """

    name: str
    id: Union[Unset, str] = UNSET
    organization: Union[Unset, str] = UNSET
    project: Union[Unset, str] = UNSET
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[Unset, None, int] = UNSET
    value_percent: Union[Unset, None, int] = UNSET
    data: Union[Unset, None, "TaskData"] = UNSET
    created: Union[Unset, datetime.datetime] = UNSET
    updated: Union[Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name
        id = self.id
        organization = self.organization
        project = self.project
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value = self.value
        value_percent = self.value_percent
        data: Union[Unset, None, Dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict() if self.data else None

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
                "name": name,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if organization is not UNSET:
            field_dict["organization"] = organization
        if project is not UNSET:
            field_dict["project"] = project
        if status is not UNSET:
            field_dict["status"] = status
        if value is not UNSET:
            field_dict["value"] = value
        if value_percent is not UNSET:
            field_dict["value_percent"] = value_percent
        if data is not UNSET:
            field_dict["data"] = data
        if created is not UNSET:
            field_dict["created"] = created
        if updated is not UNSET:
            field_dict["updated"] = updated

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.task_data import TaskData

        d = src_dict.copy()
        name = d.pop("name")

        id = d.pop("id", UNSET)

        organization = d.pop("organization", UNSET)

        project = d.pop("project", UNSET)

        _status = d.pop("status", UNSET)
        status: Union[Unset, StatusEnum]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = StatusEnum(_status)

        value = d.pop("value", UNSET)

        value_percent = d.pop("value_percent", UNSET)

        _data = d.pop("data", UNSET)
        data: Union[Unset, None, TaskData]
        if _data is None:
            data = None
        elif isinstance(_data, Unset):
            data = UNSET
        else:
            data = TaskData.from_dict(_data)

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

        task = cls(
            name=name,
            id=id,
            organization=organization,
            project=project,
            status=status,
            value=value,
            value_percent=value_percent,
            data=data,
            created=created,
            updated=updated,
        )

        task.additional_properties = d
        return task

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
