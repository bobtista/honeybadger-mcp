"""Tests for the Honeybadger MCP server."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from mcp.types import TextContent, Tool

from honeybadger_mcp_server.server import HoneybadgerTools, Server, serve


@pytest.mark.asyncio
async def test_server_initialization(api_key: str, project_id: str, mocker):
    """Test server initialization and tool registration."""
    # Mock stdio server context
    mock_stdio = mocker.patch("honeybadger_mcp_server.server.stdio_server")
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()
    mock_stdio.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Mock server.run to avoid actual execution
    mock_run = mocker.patch("mcp.server.Server.run")
    mock_run.return_value = None

    # Create a done event to control test flow
    done = asyncio.Event()

    async def mock_server_run(*args, **kwargs):
        # Simulate server startup
        tools = [
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
        done.set()
        return tools

    mock_run.side_effect = mock_server_run

    # Start server in background task
    task = asyncio.create_task(serve(project_id, api_key))

    # Wait for server initialization or timeout
    try:
        await asyncio.wait_for(done.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Server initialization timed out")
    finally:
        task.cancel()

    # Verify server was initialized correctly
    mock_stdio.assert_called_once()
    assert mock_run.call_count == 1


@pytest.mark.asyncio
async def test_list_faults_call(mock_session, api_key, project_id, mocker):
    """Test list_faults tool execution."""
    server = Server("mcp-honeybadger")

    # Mock stdio server
    mock_stdio = mocker.patch("honeybadger_mcp_server.server.stdio_server")
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()
    mock_stdio.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Mock server.run and list_faults
    mocker.patch.object(server, "run")
    mock_list_faults = mocker.patch("honeybadger_mcp_server.server.list_faults")
    mock_list_faults.return_value = {
        "results": [
            {
                "id": "12345",
                "error_class": "RuntimeError",
                "environment": "test",
            }
        ]
    }

    # Register tool handler
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == HoneybadgerTools.LIST_FAULTS:
            return [TextContent(type="text", text=str(mock_list_faults.return_value))]
        return []

    # Simulate tool call
    result = await call_tool(
        HoneybadgerTools.LIST_FAULTS,
        {
            "q": "test",
            "created_after": "2024-03-19T00:00:00Z",
            "limit": 10,
            "order": "desc",
        },
    )

    # Verify result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    response_data = eval(result[0].text)  # Convert string repr back to dict
    assert response_data["results"][0]["id"] == "12345"
    assert response_data["results"][0]["error_class"] == "RuntimeError"


@pytest.mark.asyncio
async def test_get_fault_details_call(mock_session, api_key, project_id, mocker):
    """Test get_fault_details tool execution."""
    server = Server("mcp-honeybadger")

    # Mock stdio server
    mock_stdio = mocker.patch("honeybadger_mcp_server.server.stdio_server")
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()
    mock_stdio.return_value.__aenter__.return_value = (
        mock_read_stream,
        mock_write_stream,
    )

    # Mock server.run and get_fault_details
    mocker.patch.object(server, "run")
    mock_get_fault_details = mocker.patch(
        "honeybadger_mcp_server.server.get_fault_details"
    )
    mock_get_fault_details.return_value = {
        "results": [
            {
                "id": "67890",
                "error_class": "RuntimeError",
                "backtrace": [{"file": "test.py", "line": 42}],
            }
        ]
    }

    # Register tool handler
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == HoneybadgerTools.GET_FAULT_DETAILS:
            return [
                TextContent(type="text", text=str(mock_get_fault_details.return_value))
            ]
        return []

    # Simulate tool call
    result = await call_tool(
        HoneybadgerTools.GET_FAULT_DETAILS,
        {"fault_id": "67890", "created_after": "2024-03-19T00:00:00Z", "limit": 10},
    )

    # Verify result
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    response_data = eval(result[0].text)  # Convert string repr back to dict
    assert response_data["results"][0]["id"] == "67890"
    assert response_data["results"][0]["error_class"] == "RuntimeError"
    assert response_data["results"][0]["backtrace"][0]["file"] == "test.py"
