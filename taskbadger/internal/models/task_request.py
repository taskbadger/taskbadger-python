from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

import attr

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_request_data import TaskRequestData


T = TypeVar("T", bound="TaskRequest")


@attr.s(auto_attribs=True)
class TaskRequest:
    """
    Attributes:
        name (str): Name of the task
        status (Union[Unset, StatusEnum]):  Default: StatusEnum.PENDING.
        value (Union[Unset, None, int]): Current progress value
        value_max (Union[Unset, int]): Maximum value of the task. Defaults to 100.
        data (Union[Unset, None, TaskRequestData]): Custom metadata
    """

    name: str
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[Unset, None, int] = UNSET
    value_max: Union[Unset, int] = UNSET
    data: Union[Unset, None, "TaskRequestData"] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value = self.value
        value_max = self.value_max
        data: Union[Unset, None, Dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict() if self.data else None

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if value is not UNSET:
            field_dict["value"] = value
        if value_max is not UNSET:
            field_dict["value_max"] = value_max
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.task_request_data import TaskRequestData

        d = src_dict.copy()
        name = d.pop("name")

        _status = d.pop("status", UNSET)
        status: Union[Unset, StatusEnum]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = StatusEnum(_status)

        value = d.pop("value", UNSET)

        value_max = d.pop("value_max", UNSET)

        _data = d.pop("data", UNSET)
        data: Union[Unset, None, TaskRequestData]
        if _data is None:
            data = None
        elif isinstance(_data, Unset):
            data = UNSET
        else:
            data = TaskRequestData.from_dict(_data)

        task_request = cls(
            name=name,
            status=status,
            value=value,
            value_max=value_max,
            data=data,
        )

        task_request.additional_properties = d
        return task_request

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
