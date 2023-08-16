import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union

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
        id (str): Task ID
        organization (str):
        project (str):
        name (str): Name of the task
        created (datetime.datetime):
        updated (datetime.datetime):
        url (str):
        public_url (str):
        status (Union[Unset, StatusEnum]):  Default: StatusEnum.PENDING.
        value (Union[Unset, None, int]): Current progress value.
        value_max (Union[Unset, int]): Maximum value of the task. Defaults to 100.
        value_percent (Optional[int]):
        data (Union[Unset, None, TaskData]): Custom metadata
        start_time (Union[Unset, None, datetime.datetime]): Datetime when the status is set to a running state. Can be
            set via the API.
        end_time (Union[Unset, None, datetime.datetime]): Datetime when status is set to a terminal value.Can be set via
            the API.
        max_runtime (Union[Unset, None, int]): Maximum duration the task can be running for before being considered
            failed. (seconds)
        stale_timeout (Union[Unset, None, int]): Maximum time to allow between task updates before considering the task
            stale. (seconds)
    """

    id: str
    organization: str
    project: str
    name: str
    created: datetime.datetime
    updated: datetime.datetime
    url: str
    public_url: str
    value_percent: Optional[int]
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[Unset, None, int] = UNSET
    value_max: Union[Unset, int] = UNSET
    data: Union[Unset, None, "TaskData"] = UNSET
    start_time: Union[Unset, None, datetime.datetime] = UNSET
    end_time: Union[Unset, None, datetime.datetime] = UNSET
    max_runtime: Union[Unset, None, int] = UNSET
    stale_timeout: Union[Unset, None, int] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id
        organization = self.organization
        project = self.project
        name = self.name
        created = self.created.isoformat()

        updated = self.updated.isoformat()

        url = self.url
        public_url = self.public_url
        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value = self.value
        value_max = self.value_max
        value_percent = self.value_percent
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
        field_dict.update(
            {
                "id": id,
                "organization": organization,
                "project": project,
                "name": name,
                "created": created,
                "updated": updated,
                "url": url,
                "public_url": public_url,
                "value_percent": value_percent,
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
        from ..models.task_data import TaskData

        d = src_dict.copy()
        id = d.pop("id")

        organization = d.pop("organization")

        project = d.pop("project")

        name = d.pop("name")

        created = isoparse(d.pop("created"))

        updated = isoparse(d.pop("updated"))

        url = d.pop("url")

        public_url = d.pop("public_url")

        _status = d.pop("status", UNSET)
        status: Union[Unset, StatusEnum]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = StatusEnum(_status)

        value = d.pop("value", UNSET)

        value_max = d.pop("value_max", UNSET)

        value_percent = d.pop("value_percent")

        _data = d.pop("data", UNSET)
        data: Union[Unset, None, TaskData]
        if _data is None:
            data = None
        elif isinstance(_data, Unset):
            data = UNSET
        else:
            data = TaskData.from_dict(_data)

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

        task = cls(
            id=id,
            organization=organization,
            project=project,
            name=name,
            created=created,
            updated=updated,
            url=url,
            public_url=public_url,
            status=status,
            value=value,
            value_max=value_max,
            value_percent=value_percent,
            data=data,
            start_time=start_time,
            end_time=end_time,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
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
