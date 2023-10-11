import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.patched_task_request_data import PatchedTaskRequestData


T = TypeVar("T", bound="PatchedTaskRequest")


@_attrs_define
class PatchedTaskRequest:
    """
    Attributes:
        name (Union[Unset, str]): Name of the task
        status (Union[Unset, StatusEnum]):  Default: StatusEnum.PENDING.
        value (Union[Unset, None, int]): Current progress value.
        value_max (Union[Unset, int]): Maximum value of the task. Defaults to 100.
        data (Union[Unset, None, PatchedTaskRequestData]): Custom metadata
        start_time (Union[Unset, None, datetime.datetime]): Datetime when the status is set to a running state. Can be
            set via the API.
        end_time (Union[Unset, None, datetime.datetime]): Datetime when status is set to a terminal value.Can be set via
            the API.
        max_runtime (Union[Unset, None, int]): Maximum duration the task can be running for before being considered
            failed. (seconds)
        stale_timeout (Union[Unset, None, int]): Maximum time to allow between task updates before considering the task
            stale. Only applies when task is in a running state. (seconds)
    """

    name: Union[Unset, str] = UNSET
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[Unset, None, int] = UNSET
    value_max: Union[Unset, int] = UNSET
    data: Union[Unset, None, "PatchedTaskRequestData"] = UNSET
    start_time: Union[Unset, None, datetime.datetime] = UNSET
    end_time: Union[Unset, None, datetime.datetime] = UNSET
    max_runtime: Union[Unset, None, int] = UNSET
    stale_timeout: Union[Unset, None, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

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

        start_time: Union[Unset, None, str] = UNSET
        if not isinstance(self.start_time, Unset):
            start_time = self.start_time.isoformat() if self.start_time else None

        end_time: Union[Unset, None, str] = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat() if self.end_time else None

        max_runtime = self.max_runtime
        stale_timeout = self.stale_timeout

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if status is not UNSET:
            field_dict["status"] = status
        if value is not UNSET:
            field_dict["value"] = value
        if value_max is not UNSET:
            field_dict["value_max"] = value_max
        if data is not UNSET:
            field_dict["data"] = data
        if start_time is not UNSET:
            field_dict["start_time"] = start_time
        if end_time is not UNSET:
            field_dict["end_time"] = end_time
        if max_runtime is not UNSET:
            field_dict["max_runtime"] = max_runtime
        if stale_timeout is not UNSET:
            field_dict["stale_timeout"] = stale_timeout

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

        value_max = d.pop("value_max", UNSET)

        _data = d.pop("data", UNSET)
        data: Union[Unset, None, PatchedTaskRequestData]
        if _data is None:
            data = None
        elif isinstance(_data, Unset):
            data = UNSET
        else:
            data = PatchedTaskRequestData.from_dict(_data)

        _start_time = d.pop("start_time", UNSET)
        start_time: Union[Unset, None, datetime.datetime]
        if _start_time is None:
            start_time = None
        elif isinstance(_start_time, Unset):
            start_time = UNSET
        else:
            start_time = isoparse(_start_time)

        _end_time = d.pop("end_time", UNSET)
        end_time: Union[Unset, None, datetime.datetime]
        if _end_time is None:
            end_time = None
        elif isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        max_runtime = d.pop("max_runtime", UNSET)

        stale_timeout = d.pop("stale_timeout", UNSET)

        patched_task_request = cls(
            name=name,
            status=status,
            value=value,
            value_max=value_max,
            data=data,
            start_time=start_time,
            end_time=end_time,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
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
