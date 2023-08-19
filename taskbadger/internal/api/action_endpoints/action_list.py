from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action import Action
from ...types import Response


def _get_kwargs(
    organization_slug: str,
    project_slug: str,
    task_id: str,
) -> Dict[str, Any]:
    pass

    return {
        "method": "get",
        "url": "/api/{organization_slug}/{project_slug}/tasks/{task_id}/actions/".format(
            organization_slug=organization_slug,
            project_slug=project_slug,
            task_id=task_id,
        ),
    }


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[List["Action"]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = Action.from_dict(response_200_item_data)

            response_200.append(response_200_item)

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[List["Action"]]:
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
    *,
    client: AuthenticatedClient,
) -> Response[List["Action"]]:
    """List Actions

     List actions for task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[List['Action']]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[List["Action"]]:
    """List Actions

     List actions for task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        List['Action']
    """

    return sync_detailed(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[List["Action"]]:
    """List Actions

     List actions for task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[List['Action']]
    """

    kwargs = _get_kwargs(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[List["Action"]]:
    """List Actions

     List actions for task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        List['Action']
    """

    return (
        await asyncio_detailed(
            organization_slug=organization_slug,
            project_slug=project_slug,
            task_id=task_id,
            client=client,
        )
    ).parsed
