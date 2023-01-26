from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

import attr

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.patched_task_request_data import PatchedTaskRequestData


T = TypeVar("T", bound="PatchedTaskRequest")


@attr.s(auto_attribs=True)
class PatchedTaskRequest:
    """
    Attributes:
        name (Union[Unset, str]): Name of the task
        status (Union[Unset, StatusEnum]):  Default: StatusEnum.PENDING.
        value (Union[Unset, None, int]): Current progress value
        data (Union[Unset, None, PatchedTaskRequestData]): Custom metadata
    """

    name: Union[Unset, str] = UNSET
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[Unset, None, int] = UNSET
    data: Union[Unset, None, "PatchedTaskRequestData"] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value = self.value
        data: Union[Unset, None, Dict[str, Any]] = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict() if self.data else None

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if status is not UNSET:
            field_dict["status"] = status
        if value is not UNSET:
            field_dict["value"] = value
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.patched_task_request_data import PatchedTaskRequestData

        d = src_dict.copy()
        name = d.pop("name", UNSET)

        _status = d.pop("status", UNSET)
        status: Union[Unset, StatusEnum]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = StatusEnum(_status)

        value = d.pop("value", UNSET)

        _data = d.pop("data", UNSET)
        data: Union[Unset, None, PatchedTaskRequestData]
        if _data is None:
            data = None
        elif isinstance(_data, Unset):
            data = UNSET
        else:
            data = PatchedTaskRequestData.from_dict(_data)

        patched_task_request = cls(
            name=name,
            status=status,
            value=value,
            data=data,
        )

        patched_task_request.additional_properties = d
        return patched_task_request

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
