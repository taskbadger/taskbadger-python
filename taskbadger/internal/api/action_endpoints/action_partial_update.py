from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action import Action
from ...models.patched_action_request import PatchedActionRequest
from ...types import Response


def _get_kwargs(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: str,
    *,
    json_body: PatchedActionRequest,
) -> Dict[str, Any]:
    pass

    json_json_body = json_body.to_dict()

    return {
        "method": "patch",
        "url": "/api/{organization_slug}/{project_slug}/tasks/{task_id}/actions/{id}/".format(
            organization_slug=organization_slug,
            project_slug=project_slug,
            task_id=task_id,
            id=id,
        ),
        "json": json_json_body,
    }


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Action]:
    if response.status_code == HTTPStatus.OK:
        response_200 = Action.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Action]:
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
    id: str,
    *,
    client: AuthenticatedClient,
    json_body: PatchedActionRequest,
) -> Response[Action]:
    """Update Action (partial)

     Update an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (str):
        json_body (PatchedActionRequest):

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
        json_body=json_body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: str,
    *,
    client: AuthenticatedClient,
    json_body: PatchedActionRequest,
) -> Optional[Action]:
    """Update Action (partial)

     Update an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (str):
        json_body (PatchedActionRequest):

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
        json_body=json_body,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: str,
    *,
    client: AuthenticatedClient,
    json_body: PatchedActionRequest,
) -> Response[Action]:
    """Update Action (partial)

     Update an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (str):
        json_body (PatchedActionRequest):

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
        json_body=json_body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    id: str,
    *,
    client: AuthenticatedClient,
    json_body: PatchedActionRequest,
) -> Optional[Action]:
    """Update Action (partial)

     Update an action

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        id (str):
        json_body (PatchedActionRequest):

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
            json_body=json_body,
        )
    ).parsed
