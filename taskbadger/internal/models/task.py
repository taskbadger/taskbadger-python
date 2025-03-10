import datetime
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_tags import TaskTags


T = TypeVar("T", bound="Task")


@_attrs_define
class Task:
    """
    Attributes:
        id (str): Task ID
        organization (str):
        project (str):
        name (str): Name of the task
        value_percent (Union[None, int]):
        created (datetime.datetime):
        updated (datetime.datetime):
        url (str):
        public_url (str):
        status (Union[Unset, StatusEnum]): * `pending` - pending
            * `pre_processing` - pre_processing
            * `processing` - processing
            * `post_processing` - post_processing
            * `success` - success
            * `error` - error
            * `cancelled` - cancelled
            * `stale` - stale Default: StatusEnum.PENDING.
        value (Union[None, Unset, int]): Current progress value.
        value_max (Union[Unset, int]): Maximum value of the task. Defaults to 100.
        data (Union[Unset, Any]): Custom metadata
        start_time (Union[None, Unset, datetime.datetime]): Datetime when the status is set to a running state. Can be
            set via the API.
        end_time (Union[None, Unset, datetime.datetime]): Datetime when status is set to a terminal value.Can be set via
            the API.
        max_runtime (Union[None, Unset, int]): Maximum duration the task can be running for before being considered
            failed. (seconds)
        stale_timeout (Union[None, Unset, int]): Maximum time to allow between task updates before considering the task
            stale. (seconds)
        tags (Union[Unset, TaskTags]): Tags for the task represented as a mapping from 'namespace' to 'value'.
    """

    id: str
    organization: str
    project: str
    name: str
    value_percent: Union[None, int]
    created: datetime.datetime
    updated: datetime.datetime
    url: str
    public_url: str
    status: Union[Unset, StatusEnum] = StatusEnum.PENDING
    value: Union[None, Unset, int] = UNSET
    value_max: Union[Unset, int] = UNSET
    data: Union[Unset, Any] = UNSET
    start_time: Union[None, Unset, datetime.datetime] = UNSET
    end_time: Union[None, Unset, datetime.datetime] = UNSET
    max_runtime: Union[None, Unset, int] = UNSET
    stale_timeout: Union[None, Unset, int] = UNSET
    tags: Union[Unset, "TaskTags"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        organization = self.organization

        project = self.project

        name = self.name

        value_percent: Union[None, int]
        value_percent = self.value_percent

        created = self.created.isoformat()

        updated = self.updated.isoformat()

        url = self.url

        public_url = self.public_url

        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value: Union[None, Unset, int]
        if isinstance(self.value, Unset):
            value = UNSET
        else:
            value = self.value

        value_max = self.value_max

        data = self.data

        start_time: Union[None, Unset, str]
        if isinstance(self.start_time, Unset):
            start_time = UNSET
        elif isinstance(self.start_time, datetime.datetime):
            start_time = self.start_time.isoformat()
        else:
            start_time = self.start_time

        end_time: Union[None, Unset, str]
        if isinstance(self.end_time, Unset):
            end_time = UNSET
        elif isinstance(self.end_time, datetime.datetime):
            end_time = self.end_time.isoformat()
        else:
            end_time = self.end_time

        max_runtime: Union[None, Unset, int]
        if isinstance(self.max_runtime, Unset):
            max_runtime = UNSET
        else:
            max_runtime = self.max_runtime

        stale_timeout: Union[None, Unset, int]
        if isinstance(self.stale_timeout, Unset):
            stale_timeout = UNSET
        else:
            stale_timeout = self.stale_timeout

        tags: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "organization": organization,
                "project": project,
                "name": name,
                "value_percent": value_percent,
                "created": created,
                "updated": updated,
                "url": url,
                "public_url": public_url,
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
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        from ..models.task_tags import TaskTags

        d = src_dict.copy()
        id = d.pop("id")

        organization = d.pop("organization")

        project = d.pop("project")

        name = d.pop("name")

        def _parse_value_percent(data: object) -> Union[None, int]:
            if data is None:
                return data
            return cast(Union[None, int], data)

        value_percent = _parse_value_percent(d.pop("value_percent"))

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

        def _parse_value(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        value = _parse_value(d.pop("value", UNSET))

        value_max = d.pop("value_max", UNSET)

        data = d.pop("data", UNSET)

        def _parse_start_time(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                start_time_type_0 = isoparse(data)

                return start_time_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        start_time = _parse_start_time(d.pop("start_time", UNSET))

        def _parse_end_time(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                end_time_type_0 = isoparse(data)

                return end_time_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        end_time = _parse_end_time(d.pop("end_time", UNSET))

        def _parse_max_runtime(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        max_runtime = _parse_max_runtime(d.pop("max_runtime", UNSET))

        def _parse_stale_timeout(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        stale_timeout = _parse_stale_timeout(d.pop("stale_timeout", UNSET))

        _tags = d.pop("tags", UNSET)
        tags: Union[Unset, TaskTags]
        if isinstance(_tags, Unset):
            tags = UNSET
        else:
            tags = TaskTags.from_dict(_tags)

        task = cls(
            id=id,
            organization=organization,
            project=project,
            name=name,
            value_percent=value_percent,
            created=created,
            updated=updated,
            url=url,
            public_url=public_url,
            status=status,
            value=value,
            value_max=value_max,
            data=data,
            start_time=start_time,
            end_time=end_time,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
            tags=tags,
        )

        task.additional_properties = d
        return task

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
