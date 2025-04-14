"""Honeybadger API client functions."""

import logging
from typing import Any, Dict, Optional

import aiohttp

HONEYBADGER_API_BASE_URL = "https://app.honeybadger.io/v2"

logger = logging.getLogger(__name__)


async def make_request(
    endpoint: str, params: Dict[str, Any], project_id: str, api_key: str
) -> Dict[str, Any]:
    """Make a request to the Honeybadger API.

    Args:
        endpoint: API endpoint path
        params: Query parameters
        project_id: Honeybadger project ID
        api_key: Honeybadger API key

    Returns:
        Dict containing the API response or error
    """
    url = f"{HONEYBADGER_API_BASE_URL}/projects/{project_id}{endpoint}"
    auth = aiohttp.BasicAuth(login=api_key)

    logger.debug(f"Making request to: {url}")
    logger.debug(f"With params: {params}")
    logger.debug(f"Using API key: {api_key[:4]}...")
    logger.debug(f"Using project ID: {project_id}")

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Error from Honeybadger API: {error_text}")
                return {"error": f"HTTP {response.status} - {error_text}"}

            return await response.json()


async def list_faults(
    project_id: str,
    api_key: str,
    q: Optional[str] = None,
    created_after: Optional[int] = None,
    occurred_after: Optional[int] = None,
    occurred_before: Optional[int] = None,
    limit: int = 25,
    order: str = "frequent",
) -> Dict[str, Any]:
    """List faults from Honeybadger with optional filtering.

    Args:
        project_id: Honeybadger project ID
        api_key: Honeybadger API key
        q: Search string to filter faults
        created_after: Unix timestamp to filter faults created after
        occurred_after: Unix timestamp to filter faults that occurred after
        occurred_before: Unix timestamp to filter faults that occurred before
        limit: Maximum number of faults to return (max 25)
        order: Sort order - 'recent' for most recently occurred, 'frequent' for most notifications

    Returns:
        Dict containing the list of faults or error information
    """
    params = {
        "q": q,
        "created_after": created_after,
        "occurred_after": occurred_after,
        "occurred_before": occurred_before,
        "limit": limit,
        "order": order,
    }
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    return await make_request("/faults", params, project_id, api_key)


async def get_fault_details(
    project_id: str,
    api_key: str,
    fault_id: str,
    created_after: Optional[int] = None,
    created_before: Optional[int] = None,
    limit: int = 1,
) -> Dict[str, Any]:
    """Get detailed notice information for a specific fault.

    Args:
        project_id: Honeybadger project ID
        api_key: Honeybadger API key
        fault_id: The fault ID to get details for
        created_after: Unix timestamp to filter notices created after
        created_before: Unix timestamp to filter notices created before
        limit: Maximum number of notices to return (max 25)

    Returns:
        Dict containing the fault details or error information

    Note:
        Results are always ordered by creation time descending.
    """
    params = {
        "created_after": created_after,
        "created_before": created_before,
        "limit": limit,
    }
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}

    return await make_request(
        f"/faults/{fault_id}/notices", params, project_id, api_key
    )
