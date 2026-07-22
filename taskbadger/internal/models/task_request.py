from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, Generator, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.status_enum import StatusEnum
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_request_tags import TaskRequestTags


T = TypeVar("T", bound="TaskRequest")


@_attrs_define
class TaskRequest:
    """
    Attributes:
        name (str): Name of the task
        id (str | Unset): Task ID. May be set on creation to a UUID or shortened UUID; it must be unique and is
            immutable thereafter. If omitted, an ID is generated.
        queue (str | Unset): Queue the task is from
        external_id (str | Unset): Identifier from the originating system (e.g. Celery task ID) for correlating with
            logs
        status (StatusEnum | Unset): * `pending` - pending
            * `pre_processing` - pre_processing
            * `processing` - processing
            * `post_processing` - post_processing
            * `success` - success
            * `error` - error
            * `cancelled` - cancelled
            * `stale` - stale Default: StatusEnum.PENDING.
        value (int | None | Unset): Current progress value.
        value_max (int | Unset): Maximum value of the task. Defaults to 100.
        data (Any | Unset): Custom metadata
        start_time (datetime.datetime | None | Unset): Datetime when the status is set to a running state. Can be set
            via the API.
        end_time (datetime.datetime | None | Unset): Datetime when status is set to a terminal value.Can be set via the
            API.
        time_to_start (None | str | Unset): Duration between task creation and when status first changes from pending.
            (seconds)
        max_runtime (int | None | Unset): Maximum duration the task can be running for before being considered failed.
            (seconds)
        stale_timeout (int | None | Unset): Maximum time to allow between task updates before considering the task
            stale. (seconds)
        tags (TaskRequestTags | Unset): Tags for the task represented as a mapping from 'namespace' to 'value'.
    """

    name: str
    id: str | Unset = UNSET
    queue: str | Unset = UNSET
    external_id: str | Unset = UNSET
    status: StatusEnum | Unset = StatusEnum.PENDING
    value: int | None | Unset = UNSET
    value_max: int | Unset = UNSET
    data: Any | Unset = UNSET
    start_time: datetime.datetime | None | Unset = UNSET
    end_time: datetime.datetime | None | Unset = UNSET
    time_to_start: None | str | Unset = UNSET
    max_runtime: int | None | Unset = UNSET
    stale_timeout: int | None | Unset = UNSET
    tags: TaskRequestTags | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.task_request_tags import TaskRequestTags

        name = self.name

        id = self.id

        queue = self.queue

        external_id = self.external_id

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        value: int | None | Unset
        if isinstance(self.value, Unset):
            value = UNSET
        else:
            value = self.value

        value_max = self.value_max

        data = self.data

        start_time: None | str | Unset
        if isinstance(self.start_time, Unset):
            start_time = UNSET
        elif isinstance(self.start_time, datetime.datetime):
            start_time = self.start_time.isoformat()
        else:
            start_time = self.start_time

        end_time: None | str | Unset
        if isinstance(self.end_time, Unset):
            end_time = UNSET
        elif isinstance(self.end_time, datetime.datetime):
            end_time = self.end_time.isoformat()
        else:
            end_time = self.end_time

        time_to_start: None | str | Unset
        if isinstance(self.time_to_start, Unset):
            time_to_start = UNSET
        else:
            time_to_start = self.time_to_start

        max_runtime: int | None | Unset
        if isinstance(self.max_runtime, Unset):
            max_runtime = UNSET
        else:
            max_runtime = self.max_runtime

        stale_timeout: int | None | Unset
        if isinstance(self.stale_timeout, Unset):
            stale_timeout = UNSET
        else:
            stale_timeout = self.stale_timeout

        tags: dict[str, Any] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if queue is not UNSET:
            field_dict["queue"] = queue
        if external_id is not UNSET:
            field_dict["external_id"] = external_id
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
        if time_to_start is not UNSET:
            field_dict["time_to_start"] = time_to_start
        if max_runtime is not UNSET:
            field_dict["max_runtime"] = max_runtime
        if stale_timeout is not UNSET:
            field_dict["stale_timeout"] = stale_timeout
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.task_request_tags import TaskRequestTags

        d = dict(src_dict)
        name = d.pop("name")

        id = d.pop("id", UNSET)

        queue = d.pop("queue", UNSET)

        external_id = d.pop("external_id", UNSET)

        _status = d.pop("status", UNSET)
        status: StatusEnum | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = StatusEnum(_status)

        def _parse_value(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        value = _parse_value(d.pop("value", UNSET))

        value_max = d.pop("value_max", UNSET)

        data = d.pop("data", UNSET)

        def _parse_start_time(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                start_time_type_0 = isoparse(data)

                return start_time_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        start_time = _parse_start_time(d.pop("start_time", UNSET))

        def _parse_end_time(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                end_time_type_0 = isoparse(data)

                return end_time_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        end_time = _parse_end_time(d.pop("end_time", UNSET))

        def _parse_time_to_start(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        time_to_start = _parse_time_to_start(d.pop("time_to_start", UNSET))

        def _parse_max_runtime(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_runtime = _parse_max_runtime(d.pop("max_runtime", UNSET))

        def _parse_stale_timeout(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        stale_timeout = _parse_stale_timeout(d.pop("stale_timeout", UNSET))

        _tags = d.pop("tags", UNSET)
        tags: TaskRequestTags | Unset
        if isinstance(_tags, Unset):
            tags = UNSET
        else:
            tags = TaskRequestTags.from_dict(_tags)

        task_request = cls(
            name=name,
            id=id,
            queue=queue,
            external_id=external_id,
            status=status,
            value=value,
            value_max=value_max,
            data=data,
            start_time=start_time,
            end_time=end_time,
            time_to_start=time_to_start,
            max_runtime=max_runtime,
            stale_timeout=stale_timeout,
            tags=tags,
        )

        task_request.additional_properties = d
        return task_request

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
