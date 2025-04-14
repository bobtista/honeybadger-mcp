import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, Literal, Optional

import aiohttp
from fastmcp import Context, FastMCP
from mcp.types import TextContent
from pydantic import BaseModel, ConfigDict

HONEYBADGER_API_BASE_URL = "https://app.honeybadger.io/v2"

logger = logging.getLogger(__name__)


@dataclass
class HoneybadgerContext:
    """Application context containing shared resources."""

    client: aiohttp.ClientSession
    project_id: str
    api_key: str


@asynccontextmanager
async def honeybadger_lifespan(server: FastMCP) -> AsyncIterator[HoneybadgerContext]:
    """Manage server lifecycle and resources.

    Args:
        server: The FastMCP server instance

    Yields:
        HoneybadgerContext: The context containing the shared HTTP client and configuration
    """
    project_id = os.getenv("HONEYBADGER_PROJECT_ID")
    api_key = os.getenv("HONEYBADGER_API_KEY")

    if not api_key:
        raise ValueError("HONEYBADGER_API_KEY environment variable is required")
    if not project_id:
        raise ValueError("HONEYBADGER_PROJECT_ID environment variable is required")

    # Initialize shared HTTP client on startup with auth
    auth = aiohttp.BasicAuth(login=api_key)
    client = aiohttp.ClientSession(auth=auth)
    try:
        yield HoneybadgerContext(client=client, project_id=project_id, api_key=api_key)
    finally:
        # Ensure client is properly closed on shutdown
        await client.close()


# Initialize FastMCP server with lifespan management and server config
mcp = FastMCP(
    "mcp-honeybadger",
    description="MCP server for interacting with Honeybadger API",
    lifespan=honeybadger_lifespan,
    host=os.getenv("HOST", "127.0.0.1"),
    port=int(os.getenv("PORT", "8050")),
)


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


async def make_request(
    ctx: Context, endpoint: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Make a request to the Honeybadger API using the shared client."""
    honeybadger_ctx = ctx.request_context.lifespan_context
    url = f"{HONEYBADGER_API_BASE_URL}/projects/{honeybadger_ctx.project_id}{endpoint}"

    logger.debug(f"Making request to: {url}")
    logger.debug(f"With params: {params}")
    logger.debug(
        f"Using API key: {honeybadger_ctx.api_key[:4]}..."
    )  # Only log first 4 chars for security
    logger.debug(f"Using project ID: {honeybadger_ctx.project_id}")

    async with honeybadger_ctx.client.get(url, params=params) as response:
        if response.status != 200:
            error_text = await response.text()
            logger.error(f"Error from Honeybadger API: {error_text}")
            return {"error": f"HTTP {response.status} - {error_text}"}

        return await response.json()


@mcp.tool()
async def list_faults(
    ctx: Context,
    q: Optional[str] = None,
    created_after: Optional[int] = None,
    occurred_after: Optional[int] = None,
    occurred_before: Optional[int] = None,
    limit: int = 25,
    order: str = "frequent",
) -> str:
    """List faults from Honeybadger with optional filtering.

    Args:
        ctx: The MCP context containing shared resources
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

    result = await make_request(ctx, "/faults", params)
    return json.dumps(
        {"error": result["error"]} if "error" in result else {"faults": result},
        indent=2,
    )


@mcp.tool()
async def get_fault_details(
    ctx: Context,
    fault_id: str,
    created_after: Optional[int] = None,
    created_before: Optional[int] = None,
    limit: int = 1,
) -> str:
    """Get detailed notice information for a specific fault.

    Args:
        ctx: The MCP context containing shared resources
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

    result = await make_request(ctx, f"/faults/{fault_id}/notices", params)
    return json.dumps(
        {"error": result["error"]} if "error" in result else {"notices": result},
        indent=2,
    )


async def main():
    """Entry point for the MCP server"""
    transport = os.getenv("TRANSPORT", "sse")  # Default to SSE transport

    if transport == "sse":
        logger.info(f"Starting server with SSE transport on {mcp.host}:{mcp.port}")
        await mcp.run_sse_async()
    else:
        logger.info("Starting server with stdio transport")
        await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    # Configure logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
