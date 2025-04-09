"""Tests for the Honeybadger API client functions."""

from datetime import datetime, timezone

import pytest
from aiohttp import ClientSession

from honeybadger_mcp_server.server import get_fault_details, list_faults


@pytest.mark.asyncio
async def test_list_faults(
    mock_session: ClientSession,
    api_key: str,
    project_id: str,
    mock_fault_response: dict,
    mocker,
):
    """Test listing faults."""
    # Mock make_request
    mock_make_request = mocker.patch("honeybadger_mcp_server.server.make_request")
    mock_make_request.return_value = mock_fault_response

    # Use Unix timestamp for created_after (2024-03-19T00:00:00Z)
    created_after = int(datetime(2024, 3, 19, tzinfo=timezone.utc).timestamp())

    # Test with explicit order
    result = await list_faults(
        project_id=project_id,
        api_key=api_key,
        q="test error",
        created_after=created_after,
        limit=25,
        order="recent",
    )

    assert result == mock_fault_response
    mock_make_request.assert_called_once_with(
        "/faults",
        {
            "q": "test error",
            "created_after": created_after,
            "limit": 25,
            "order": "recent",
        },
        project_id,
        api_key,
    )

    # Test with default order
    mock_make_request.reset_mock()
    result = await list_faults(
        project_id=project_id,
        api_key=api_key,
        q="test error",
        created_after=created_after,
        limit=25,
    )

    assert result == mock_fault_response
    mock_make_request.assert_called_once_with(
        "/faults",
        {
            "q": "test error",
            "created_after": created_after,
            "limit": 25,
            "order": "frequent",
        },
        project_id,
        api_key,
    )


@pytest.mark.asyncio
async def test_get_fault_details(
    mock_session: ClientSession,
    api_key: str,
    project_id: str,
    mock_fault_details_response: dict,
    mocker,
):
    """Test getting fault details."""
    # Mock make_request
    mock_make_request = mocker.patch("honeybadger_mcp_server.server.make_request")
    mock_make_request.return_value = mock_fault_details_response

    # Use Unix timestamp for created_after (2024-03-19T00:00:00Z)
    created_after = int(datetime(2024, 3, 19, tzinfo=timezone.utc).timestamp())

    result = await get_fault_details(
        project_id=project_id,
        api_key=api_key,
        fault_id="67890",
        created_after=created_after,
        limit=1,
    )

    assert result == mock_fault_details_response
    mock_make_request.assert_called_once_with(
        "/faults/67890/notices",
        {
            "created_after": created_after,
            "limit": 1,
        },
        project_id,
        api_key,
    )


@pytest.mark.asyncio
async def test_list_faults_error(
    mock_session: ClientSession,
    api_key: str,
    project_id: str,
    mocker,
):
    """Test error handling when listing faults."""
    # Mock make_request with error response
    mock_make_request = mocker.patch("honeybadger_mcp_server.server.make_request")
    mock_make_request.return_value = {"error": "HTTP 401 - Unauthorized"}

    result = await list_faults(
        project_id=project_id,
        api_key="invalid_key",
        limit=25,
    )

    assert "error" in result
    assert "401" in result["error"]
    mock_make_request.assert_called_once_with(
        "/faults",
        {"limit": 25, "order": "frequent"},
        project_id,
        "invalid_key",
    )
