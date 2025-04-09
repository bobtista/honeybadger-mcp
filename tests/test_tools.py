"""Tests for the Honeybadger MCP tools."""

import pytest
from mcp.types import Tool

from honeybadger_mcp_server.server import HoneybadgerTools, ListFaultsRequest


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test that the server exposes the expected tools."""

    # Register tools
    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=HoneybadgerTools.LIST_FAULTS,
                description="List faults from Honeybadger with optional filtering",
                inputSchema=ListFaultsRequest.model_json_schema(),
            ),
            Tool(
                name=HoneybadgerTools.GET_FAULT_DETAILS,
                description="Get detailed notice information for a specific fault",
                inputSchema={"type": "object"},
            ),
        ]

    tools = await list_tools()
    tool_names = {tool.name for tool in tools}
    assert tool_names == {
        HoneybadgerTools.LIST_FAULTS,
        HoneybadgerTools.GET_FAULT_DETAILS,
    }


@pytest.mark.asyncio
async def test_list_faults_schema(mcp_server):
    """Test that the list_faults tool has the correct schema."""

    # Register tools
    @mcp_server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=HoneybadgerTools.LIST_FAULTS,
                description="List faults from Honeybadger with optional filtering",
                inputSchema=ListFaultsRequest.model_json_schema(),
            ),
            Tool(
                name=HoneybadgerTools.GET_FAULT_DETAILS,
                description="Get detailed notice information for a specific fault",
                inputSchema={"type": "object"},
            ),
        ]

    tools = await list_tools()
    list_faults_tool = next(
        tool for tool in tools if tool.name == HoneybadgerTools.LIST_FAULTS
    )

    schema = list_faults_tool.inputSchema
    assert schema["type"] == "object"
    assert "q" in schema["properties"]
    assert "created_after" in schema["properties"]
    assert "limit" in schema["properties"]
    assert "order" in schema["properties"]

    # Verify order enum values and default
    order_schema = schema["properties"]["order"]
    assert order_schema["type"] == "string"
    assert set(order_schema["enum"]) == {"recent", "frequent"}
    assert order_schema["default"] == "frequent"  # Default order should be 'frequent'
