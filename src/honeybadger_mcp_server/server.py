"""Server implementation for the Honeybadger MCP server."""

import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional

import aiohttp
from fastmcp import Context, FastMCP

from honeybadger_mcp_server.api import get_fault_details, list_faults

logger = logging.getLogger(__name__)


class HoneybadgerTools(str, Enum):
    """Enum of available Honeybadger tools."""

    LIST_FAULTS = "list_faults"
    GET_FAULT_DETAILS = "get_fault_details"


@dataclass
class HoneybadgerContext:
    """Application context containing shared resources."""

    client: aiohttp.ClientSession
    project_id: str
    api_key: str


@asynccontextmanager
async def honeybadger_lifespan(
    server: FastMCP, project_id: str, api_key: str
) -> AsyncIterator[HoneybadgerContext]:
    """Manage server lifecycle and resources.

    Args:
        server: The FastMCP server instance
        project_id: The Honeybadger project ID
        api_key: The Honeybadger API key

    Yields:
        HoneybadgerContext: The context containing the shared HTTP client and configuration
    """
    if not api_key:
        raise ValueError("Honeybadger API key is required")
    if not project_id:
        raise ValueError("Honeybadger project ID is required")

    # Initialize shared HTTP client on startup with auth
    auth = aiohttp.BasicAuth(login=api_key)
    client = aiohttp.ClientSession(auth=auth)
    try:
        yield HoneybadgerContext(client=client, project_id=project_id, api_key=api_key)
    finally:
        # Ensure client is properly closed on shutdown
        await client.close()


def create_mcp_server(
    project_id: str,
    api_key: str,
    host: str = "127.0.0.1",
    port: int = 8050,
) -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        project_id: The Honeybadger project ID
        api_key: The Honeybadger API key
        host: The host to bind to (default: 127.0.0.1)
        port: The port to listen on (default: 8050)

    Returns:
        FastMCP: The configured server instance
    """
    # Initialize FastMCP server with lifespan management and server config
    server = FastMCP(
        "mcp-honeybadger",
        description="MCP server for interacting with Honeybadger API",
        lifespan=lambda s: honeybadger_lifespan(s, project_id, api_key),
        host=host,
        port=port,
    )

    # Register tools
    @server.tool()
    async def list_faults_tool(
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
        honeybadger_ctx = ctx.request_context.lifespan_context
        result = await list_faults(
            project_id=honeybadger_ctx.project_id,
            api_key=honeybadger_ctx.api_key,
            q=q,
            created_after=created_after,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            limit=limit,
            order=order,
        )
        return json.dumps(result, indent=2)

    @server.tool()
    async def get_fault_details_tool(
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
        honeybadger_ctx = ctx.request_context.lifespan_context
        result = await get_fault_details(
            project_id=honeybadger_ctx.project_id,
            api_key=honeybadger_ctx.api_key,
            fault_id=fault_id,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
        )
        return json.dumps(result, indent=2)

    return server


async def serve(
    project_id: str,
    api_key: str,
    transport: str = "sse",
    host: str = "127.0.0.1",
    port: int = 8050,
) -> None:
    """Start the MCP server with the configured transport.

    Args:
        project_id: The Honeybadger project ID
        api_key: The Honeybadger API key
        transport: The transport protocol to use (sse or stdio)
        host: The host to bind to when using SSE transport
        port: The port to listen on when using SSE transport
    """
    server = create_mcp_server(project_id, api_key, host, port)

    if transport == "sse":
        logger.info(f"Starting server with SSE transport on {host}:{port}")
        await server.run_sse_async()
    else:
        logger.info("Starting server with stdio transport")
        await server.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    # Configure logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(serve())
