from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.paginated_task_list import PaginatedTaskList
from ...types import UNSET, Response, Unset


def _get_kwargs(
    organization_slug: str,
    project_slug: str,
    *,
    cursor: Union[Unset, None, str] = UNSET,
    page_size: Union[Unset, None, int] = UNSET,
) -> dict[str, Any]:
    pass

    params: dict[str, Any] = {}
    params["cursor"] = cursor

    params["page_size"] = page_size

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    return {
        "method": "get",
        "url": f"/api/{organization_slug}/{project_slug}/tasks/",
        "params": params,
    }


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[PaginatedTaskList]:
    if response.status_code == HTTPStatus.OK:
        response_200 = PaginatedTaskList.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[PaginatedTaskList]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    organization_slug: str,
    project_slug: str,
    *,
    client: AuthenticatedClient,
    cursor: Union[Unset, None, str] = UNSET,
    page_size: Union[Unset, None, int] = UNSET,
) -> Response[PaginatedTaskList]:
    """List Tasks

     List all tasks

    Args:
        organization_slug (str):
        project_slug (str):
        cursor (Union[Unset, None, str]):
        page_size (Union[Unset, None, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code
            and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PaginatedTaskList]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        cursor=cursor,
        page_size=page_size,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    organization_slug: str,
    project_slug: str,
    *,
    client: AuthenticatedClient,
    cursor: Union[Unset, None, str] = UNSET,
    page_size: Union[Unset, None, int] = UNSET,
) -> Optional[PaginatedTaskList]:
    """List Tasks

     List all tasks

    Args:
        organization_slug (str):
        project_slug (str):
        cursor (Union[Unset, None, str]):
        page_size (Union[Unset, None, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code
            and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PaginatedTaskList
    """

    return sync_detailed(
        organization_slug=organization_slug,
        project_slug=project_slug,
        client=client,
        cursor=cursor,
        page_size=page_size,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    *,
    client: AuthenticatedClient,
    cursor: Union[Unset, None, str] = UNSET,
    page_size: Union[Unset, None, int] = UNSET,
) -> Response[PaginatedTaskList]:
    """List Tasks

     List all tasks

    Args:
        organization_slug (str):
        project_slug (str):
        cursor (Union[Unset, None, str]):
        page_size (Union[Unset, None, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code
            and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PaginatedTaskList]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        cursor=cursor,
        page_size=page_size,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    *,
    client: AuthenticatedClient,
    cursor: Union[Unset, None, str] = UNSET,
    page_size: Union[Unset, None, int] = UNSET,
) -> Optional[PaginatedTaskList]:
    """List Tasks

     List all tasks

    Args:
        organization_slug (str):
        project_slug (str):
        cursor (Union[Unset, None, str]):
        page_size (Union[Unset, None, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code
            and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PaginatedTaskList
    """

    return (
        await asyncio_detailed(
            organization_slug=organization_slug,
            project_slug=project_slug,
            client=client,
            cursor=cursor,
            page_size=page_size,
        )
    ).parsed
