"""Tests for the Honeybadger MCP tools."""

import pytest

from honeybadger_mcp_server.server import create_mcp_server


@pytest.mark.asyncio
async def test_list_tools(api_key: str, project_id: str):
    """Test listing available tools."""
    server = create_mcp_server(project_id, api_key)

    # Register tools
    @server.tool(name="list_faults")
    async def list_faults_tool():
        return '{"results": []}'

    @server.tool(name="get_fault_details")
    async def get_fault_details_tool():
        return '{"results": []}'

    tools = server.list_tools()
    tool_names = [tool.name for tool in tools]
    assert "list_faults" in tool_names
    assert "get_fault_details" in tool_names


@pytest.mark.asyncio
async def test_list_faults_schema(api_key: str, project_id: str):
    """Test list_faults tool schema validation."""
    server = create_mcp_server(project_id, api_key)

    @server.tool(name="list_faults")
    async def list_faults_tool(
        q: str = None,
        created_after: str = None,
        limit: int = 25,
        order: str = "frequent",
    ) -> str:
        return '{"results": []}'

    tool = next(t for t in server.list_tools() if t.name == "list_faults")
    schema = tool.parameters

    assert "q" in schema["properties"]
    assert schema["properties"]["q"]["type"] == "string"
    assert schema["properties"]["q"].get("required", False) is False

    assert "limit" in schema["properties"]
    assert schema["properties"]["limit"]["type"] == "integer"
    assert schema["properties"]["limit"]["default"] == 25

    assert "order" in schema["properties"]
    assert schema["properties"]["order"]["type"] == "string"
    assert schema["properties"]["order"]["default"] == "frequent"


@pytest.mark.asyncio
async def test_get_fault_details_schema(api_key: str, project_id: str):
    """Test get_fault_details tool schema validation."""
    server = create_mcp_server(project_id, api_key)

    @server.tool(name="get_fault_details")
    async def get_fault_details_tool(
        fault_id: str,
        created_after: str = None,
        limit: int = 1,
    ) -> str:
        return '{"results": []}'

    tool = next(t for t in server.list_tools() if t.name == "get_fault_details")
    schema = tool.parameters

    assert "fault_id" in schema["properties"]
    assert schema["properties"]["fault_id"]["type"] == "string"
    assert "fault_id" in schema.get("required", [])

    assert "limit" in schema["properties"]
    assert schema["properties"]["limit"]["type"] == "integer"
    assert schema["properties"]["limit"]["default"] == 1
