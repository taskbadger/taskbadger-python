from http import HTTPStatus
from typing import Any, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action import Action
from ...types import Response


def _get_kwargs(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: UUID,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/api/{organization_slug}/{project_slug}/tasks/{task_id}/actions/{id}/",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Action]:
    if response.status_code == 200:
        response_200 = Action.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Action]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[Action]:
    """Get Action

     Fetch an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Action]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: UUID,
    *,
    client: AuthenticatedClient,
) -> Optional[Action]:
    """Get Action

     Fetch an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Action
    """

    return sync_detailed(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
        id=id,
        client=client,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[Action]:
    """Get Action

     Fetch an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Action]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: UUID,
    *,
    client: AuthenticatedClient,
) -> Optional[Action]:
    """Get Action

     Fetch an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Action
    """

    return (
        await asyncio_detailed(
            organization_slug=organization_slug,
            project_slug=project_slug,
            task_id=task_id,
            id=id,
            client=client,
        )
    ).parsed
