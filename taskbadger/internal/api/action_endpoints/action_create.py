from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action import Action
from ...models.action_request import ActionRequest
from ...types import Response


def _get_kwargs(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    body: ActionRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/api/{organization_slug}/{project_slug}/tasks/{task_id}/actions/",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Action]:
    if response.status_code == 201:
        response_201 = Action.from_dict(response.json())

        return response_201
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
    *,
    client: AuthenticatedClient,
    body: ActionRequest,
) -> Response[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        body (ActionRequest):

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
        body=body,
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
    body: ActionRequest,
) -> Optional[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        body (ActionRequest):

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
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: ActionRequest,
) -> Response[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        body (ActionRequest):

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
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
    body: ActionRequest,
) -> Optional[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        body (ActionRequest):

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
            client=client,
            body=body,
        )
    ).parsed
