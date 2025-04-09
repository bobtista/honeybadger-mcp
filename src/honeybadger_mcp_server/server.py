import logging
from enum import Enum
from typing import Any, Dict, Literal, Optional

import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, ConfigDict

HONEYBADGER_API_BASE_URL = "https://app.honeybadger.io/v2"

logger = logging.getLogger(__name__)


# Request Models
class ListFaultsRequest(BaseModel):
    q: Optional[str] = None
    created_after: Optional[int] = None
    occurred_after: Optional[int] = None
    occurred_before: Optional[int] = None
    limit: int = 25
    order: Literal["recent", "frequent"] = "frequent"

    model_config = ConfigDict(
        json_schema_extra={
            "properties": {
                "q": {
                    "type": "string",
                    "description": "A search string",
                },
                "created_after": {
                    "type": "integer",
                    "description": "A Unix timestamp (number of seconds since the epoch)",
                },
                "occurred_after": {
                    "type": "integer",
                    "description": "A Unix timestamp (number of seconds since the epoch)",
                },
                "occurred_before": {
                    "type": "integer",
                    "description": "A Unix timestamp (number of seconds since the epoch)",
                },
                "limit": {
                    "type": "integer",
                    "maximum": 25,
                    "default": 25,
                    "description": "Number of results to return (max and default are 25)",
                },
                "order": {
                    "type": "string",
                    "enum": ["recent", "frequent"],
                    "default": "frequent",
                    "description": "Order results by: 'recent' (most recently occurred first) or 'frequent' (most notifications first)",
                },
            }
        }
    )


class GetFaultDetailsRequest(BaseModel):
    fault_id: str
    created_after: Optional[int] = None
    created_before: Optional[int] = None
    limit: int = 1

    model_config = ConfigDict(
        json_schema_extra={
            "properties": {
                "fault_id": {
                    "type": "string",
                    "description": "The fault ID to get details for",
                },
                "created_after": {"type": "integer", "description": "Unix timestamp"},
                "created_before": {"type": "integer", "description": "Unix timestamp"},
                "limit": {"type": "integer", "maximum": 25, "default": 1},
            },
            "required": ["fault_id"],
            "description": "Get detailed notice information for a specific fault. Results are always ordered by creation time descending.",
        }
    )


class HoneybadgerTools(str, Enum):
    LIST_FAULTS = "list_faults"
    GET_FAULT_DETAILS = "get_fault_details"


async def make_request(
    endpoint: str, params: Dict[str, Any], project_id: str, api_key: str
) -> Dict[str, Any]:
    """Make a request to the Honeybadger API"""
    url = f"{HONEYBADGER_API_BASE_URL}/projects/{project_id}{endpoint}"

    # Use API key as username with no password for Basic Auth
    auth = aiohttp.BasicAuth(login=api_key)

    logger.debug(f"Making request to: {url}")
    logger.debug(f"With params: {params}")
    logger.debug(
        f"Using API key: {api_key[:4]}..."
    )  # Only log first 4 chars for security
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
    order: Optional[str] = "frequent",
) -> Dict[str, Any]:
    """List faults from Honeybadger.

    Args:
        project_id: The Honeybadger project ID
        api_key: The Honeybadger API key
        q: Search string to filter faults
        created_after: Unix timestamp to filter faults created after
        occurred_after: Unix timestamp to filter faults that occurred after
        occurred_before: Unix timestamp to filter faults that occurred before
        limit: Maximum number of faults to return (max 25)
        order: Sort order - 'recent' for most recently occurred, 'frequent' for most notifications
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
        project_id: The Honeybadger project ID
        api_key: The Honeybadger API key
        fault_id: The fault ID to get details for
        created_after: Unix timestamp to filter notices created after
        created_before: Unix timestamp to filter notices created before
        limit: Maximum number of notices to return (max 25)

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


async def serve(project_id: str, api_key: str) -> None:
    """Start the MCP server"""
    if not api_key:
        raise ValueError("Honeybadger API key is required")
    if not project_id:
        raise ValueError("Honeybadger Project ID is required")

    server = Server("mcp-honeybadger")

    @server.list_tools()
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
                inputSchema=GetFaultDetailsRequest.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            match name:
                case HoneybadgerTools.LIST_FAULTS:
                    request = ListFaultsRequest(**arguments)
                    result = await list_faults(
                        project_id,
                        api_key,
                        request.q,
                        request.created_after,
                        request.occurred_after,
                        request.occurred_before,
                        request.limit,
                        request.order,
                    )

                case HoneybadgerTools.GET_FAULT_DETAILS:
                    result = await get_fault_details(
                        project_id,
                        api_key,
                        arguments["fault_id"],
                        arguments.get("created_after"),
                        arguments.get("created_before"),
                        arguments.get("limit", 1),
                    )

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return [TextContent(type="text", text=str({"error": str(e)}))]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
