from http import HTTPStatus
from typing import Any, Dict, Optional

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
    client: AuthenticatedClient,
    json_body: ActionRequest,
) -> Dict[str, Any]:
    url = "{}/api/{organization_slug}/{project_slug}/tasks/{task_id}/actions/".format(
        client.base_url, organization_slug=organization_slug, project_slug=project_slug, task_id=task_id
    )

    headers: Dict[str, str] = client.get_headers()
    cookies: Dict[str, Any] = client.get_cookies()

    json_json_body = json_body.to_dict()

    return {
        "method": "post",
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "timeout": client.get_timeout(),
        "json": json_json_body,
    }


def _parse_response(*, client: Client, response: httpx.Response) -> Optional[Action]:
    if response.status_code == HTTPStatus.CREATED:
        response_201 = Action.from_dict(response.json())

        return response_201
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(f"Unexpected status code: {response.status_code}")
    else:
        return None


def _build_response(*, client: Client, response: httpx.Response) -> Response[Action]:
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
    json_body: ActionRequest,
) -> Response[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        json_body (ActionRequest):

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
        client=client,
        json_body=json_body,
    )

    response = httpx.request(
        verify=client.verify_ssl,
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
    json_body: ActionRequest,
) -> Optional[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        json_body (ActionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Action]
    """

    return sync_detailed(
        organization_slug=organization_slug,
        project_slug=project_slug,
        task_id=task_id,
        client=client,
        json_body=json_body,
    ).parsed


async def asyncio_detailed(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
    json_body: ActionRequest,
) -> Response[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        json_body (ActionRequest):

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
        client=client,
        json_body=json_body,
    )

    async with httpx.AsyncClient(verify=client.verify_ssl) as _client:
        response = await _client.request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    organization_slug: str,
    project_slug: str,
    task_id: str,
    *,
    client: AuthenticatedClient,
    json_body: ActionRequest,
) -> Optional[Action]:
    """Create Action

     Create an action for a task

    Args:
        organization_slug (str):
        project_slug (str):
        task_id (str):
        json_body (ActionRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Action]
    """

    return (
        await asyncio_detailed(
            organization_slug=organization_slug,
            project_slug=project_slug,
            task_id=task_id,
            client=client,
            json_body=json_body,
        )
    ).parsed
