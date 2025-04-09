"""Test configuration and fixtures for Honeybadger MCP server tests."""

import json
from typing import Dict

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from mcp.types import TextContent, Tool

from honeybadger_mcp_server.server import HoneybadgerTools, Server


@pytest.fixture
def api_key() -> str:
    """Return a dummy API key."""
    return "test_api_key"


@pytest.fixture
def project_id() -> str:
    """Return a dummy project ID."""
    return "test_project_id"


@pytest.fixture
def mock_fault_response() -> Dict:
    """Return a mock fault list response."""
    return {
        "results": [
            {
                "id": "12345",
                "error_class": "RuntimeError",
                "message": "Test error",
                "environment": "test",
                "created_at": "2024-03-20T12:00:00Z",
                "last_notice_at": "2024-03-20T12:00:00Z",
                "notices_count": 1,
            }
        ]
    }


@pytest.fixture
def mock_fault_details_response() -> Dict:
    """Return a mock fault details response."""
    return {
        "results": [
            {
                "id": "67890",
                "error_class": "RuntimeError",
                "message": "Test error details",
                "environment": "test",
                "created_at": "2024-03-20T12:00:00Z",
                "backtrace": [{"file": "test.py", "line": 42, "method": "test_method"}],
            }
        ]
    }


@pytest_asyncio.fixture
async def mock_session(mocker, mock_fault_response, mock_fault_details_response):
    """Create a mock aiohttp session."""
    mock_response = mocker.AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = mock_fault_response
    mock_response.text.return_value = "Success"

    mock_details_response = mocker.AsyncMock()
    mock_details_response.status = 200
    mock_details_response.json.return_value = mock_fault_details_response
    mock_details_response.text.return_value = "Success"

    mock_session = mocker.AsyncMock(spec=ClientSession)
    mock_context = mocker.AsyncMock()
    mock_context.__aenter__.side_effect = [mock_response, mock_details_response]
    mock_session.get.return_value = mock_context

    return mock_session


@pytest_asyncio.fixture
async def mcp_server(api_key: str, project_id: str, mocker) -> Server:
    """Create a test MCP server instance."""
    server = Server("mcp-honeybadger")

    # Register tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=HoneybadgerTools.LIST_FAULTS,
                description="List faults from Honeybadger with optional filtering",
                inputSchema={"type": "object"},
            ),
            Tool(
                name=HoneybadgerTools.GET_FAULT_DETAILS,
                description="Get detailed notice information for a specific fault",
                inputSchema={"type": "object"},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == HoneybadgerTools.LIST_FAULTS:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "results": [
                                {
                                    "id": "12345",
                                    "error_class": "RuntimeError",
                                    "environment": "test",
                                }
                            ]
                        }
                    ),
                )
            ]
        elif name == HoneybadgerTools.GET_FAULT_DETAILS:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "results": [
                                {
                                    "id": "67890",
                                    "error_class": "RuntimeError",
                                    "backtrace": [{"file": "test.py", "line": 42}],
                                }
                            ]
                        }
                    ),
                )
            ]
        return []

    return server
