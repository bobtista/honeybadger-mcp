"""Test fixtures for the Honeybadger MCP server."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponse, ClientSession
from fastmcp import FastMCP

from honeybadger_mcp_server.server import HoneybadgerTools, create_mcp_server


@pytest.fixture
def api_key() -> str:
    """Return a dummy API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def project_id() -> str:
    """Return a dummy project ID for testing."""
    return "test_project_67890"


@pytest.fixture
def mock_fault_response() -> dict:
    """Return a mock response for list_faults."""
    return {
        "results": [
            {
                "id": "12345",
                "error_class": "RuntimeError",
                "environment": "test",
                "message": "Test error message",
                "created_at": "2024-03-19T00:00:00Z",
                "resolved": False,
            }
        ]
    }


@pytest.fixture
def mock_fault_details_response() -> dict:
    """Return a mock response for get_fault_details."""
    return {
        "results": [
            {
                "id": "67890",
                "error_class": "RuntimeError",
                "environment": "test",
                "message": "Test error details",
                "created_at": "2024-03-19T00:00:00Z",
                "backtrace": [{"file": "test.py", "line": 42, "method": "test_method"}],
            }
        ]
    }


@pytest.fixture
def mock_session(mock_fault_response, mock_fault_details_response):
    """Create a mock aiohttp session for testing."""
    session = MagicMock(spec=ClientSession)

    async def mock_get(url: str, **kwargs):
        response = AsyncMock(spec=ClientResponse)
        response.status = 200

        if "faults" in url and "notices" not in url:
            mock_data = mock_fault_response
        else:
            mock_data = mock_fault_details_response

        async def mock_json():
            return mock_data

        response.json = mock_json
        return response

    session.get = mock_get
    return session


@pytest.fixture
def mcp_server(api_key: str, project_id: str, mock_session: ClientSession) -> FastMCP:
    """Create a test instance of the MCP server."""
    server = create_mcp_server(project_id, api_key)

    # Register mock session in the lifespan context
    server.lifespan_context = MagicMock()
    server.lifespan_context.client = mock_session
    server.lifespan_context.api_key = api_key
    server.lifespan_context.project_id = project_id

    return server
