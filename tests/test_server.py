"""Tests for the Honeybadger MCP server."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP
from mcp.types import TextContent, Tool

from honeybadger_mcp_server.server import HoneybadgerTools, create_mcp_server, serve


@pytest.mark.asyncio
async def test_server_initialization(api_key: str, project_id: str, mocker):
    """Test server initialization and tool registration."""
    # Create server instance
    server = create_mcp_server(project_id, api_key)

    # Mock server.run to avoid actual execution
    mock_run = mocker.patch.object(server, "run_stdio_async")
    mock_run.return_value = None

    # Start server in background
    task = asyncio.create_task(server.run_stdio_async())

    # Give the server a moment to initialize
    await asyncio.sleep(0.1)

    # Verify server is initialized
    assert server._tool_manager is not None

    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_list_faults_call(mock_session, api_key, project_id, mocker):
    """Test list_faults tool execution."""
    server = create_mcp_server(project_id, api_key)

    # Register tools
    @server.tool(name="list_faults")
    async def list_faults_tool(
        q: str = None,
        created_after: str = None,
        limit: int = 25,
        order: str = "frequent",
    ) -> str:
        return '{"results": []}'

    # Simulate tool call
    result = await server.call_tool(
        "list_faults",
        {
            "q": "test",
            "created_after": "2024-03-19T00:00:00Z",
            "limit": 10,
            "order": "desc",
        },
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == '{"results": []}'


@pytest.mark.asyncio
async def test_get_fault_details_call(mock_session, api_key, project_id, mocker):
    """Test get_fault_details tool execution."""
    server = create_mcp_server(project_id, api_key)

    # Register tools
    @server.tool(name="get_fault_details")
    async def get_fault_details_tool(
        fault_id: str,
        created_after: str = None,
        limit: int = 1,
    ) -> str:
        return '{"results": []}'

    # Simulate tool call
    result = await server.call_tool(
        "get_fault_details",
        {"fault_id": "67890", "created_after": "2024-03-19T00:00:00Z", "limit": 10},
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == '{"results": []}'


@pytest.mark.asyncio
async def test_server_configuration():
    """Test server configuration with different parameters."""
    # Test default configuration
    server = create_mcp_server("test_project", "test_key")
    assert isinstance(server, FastMCP)

    # Test custom configuration
    server = create_mcp_server("test_project", "test_key", host="0.0.0.0", port=9000)
    assert isinstance(server, FastMCP)


@pytest.mark.asyncio
async def test_server_transport_selection(mocker):
    """Test server transport selection."""
    # Mock the server creation and transport methods
    mock_server = mocker.Mock(spec=FastMCP)
    mock_server.run_sse_async = AsyncMock()
    mock_server.run_stdio_async = AsyncMock()
    mock_server.host = "127.0.0.1"
    mock_server.port = 8050

    mocker.patch(
        "honeybadger_mcp_server.server.create_mcp_server", return_value=mock_server
    )

    # Test SSE transport
    task = asyncio.create_task(serve("test_project", "test_key", transport="sse"))
    await asyncio.sleep(0.1)  # Give it time to start
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert mock_server.run_sse_async.called
    assert not mock_server.run_stdio_async.called

    # Reset mock calls
    mock_server.run_sse_async.reset_mock()
    mock_server.run_stdio_async.reset_mock()

    # Test STDIO transport
    task = asyncio.create_task(serve("test_project", "test_key", transport="stdio"))
    await asyncio.sleep(0.1)  # Give it time to start
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert mock_server.run_stdio_async.called
    assert not mock_server.run_sse_async.called
