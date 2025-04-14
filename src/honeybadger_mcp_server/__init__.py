"""Honeybadger MCP Server - A FastMCP server for interacting with Honeybadger API."""

import logging
import sys
from importlib.metadata import version

import click

from honeybadger_mcp_server.api import get_fault_details, list_faults
from honeybadger_mcp_server.server import (
    HoneybadgerContext,
    HoneybadgerTools,
    create_mcp_server,
    serve,
)

try:
    __version__ = version("honeybadger-mcp-server")
except Exception:
    # Default to unknown version if package is not installed
    __version__ = "unknown"

__all__ = [
    "create_mcp_server",
    "serve",
    "HoneybadgerTools",
    "HoneybadgerContext",
    "list_faults",
    "get_fault_details",
]


@click.command()
@click.option(
    "--api-key",
    "-k",
    type=str,
    envvar="HONEYBADGER_API_KEY",
    help="Honeybadger API key",
)
@click.option(
    "--project-id",
    "-p",
    type=str,
    envvar="HONEYBADGER_PROJECT_ID",
    help="Honeybadger Project ID",
)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["sse", "stdio"]),
    default="sse",
    envvar="TRANSPORT",
    help="Transport protocol to use",
)
@click.option(
    "--host",
    "-h",
    type=str,
    default="127.0.0.1",
    envvar="HOST",
    help="Host to bind to when using SSE transport",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8050,
    envvar="PORT",
    help="Port to listen on when using SSE transport",
)
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
def main(
    api_key: str | None,
    project_id: str | None,
    transport: str,
    host: str,
    port: int,
    verbose: bool,
) -> None:
    """MCP Honeybadger Server - Honeybadger API functionality for MCP."""
    import asyncio

    if not api_key:
        raise click.ClickException(
            "Honeybadger API key is required. Set it via --api-key or HONEYBADGER_API_KEY environment variable"
        )

    if not project_id:
        raise click.ClickException(
            "Honeybadger Project ID is required. Set it via --project-id or HONEYBADGER_PROJECT_ID environment variable"
        )

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)

    asyncio.run(serve(project_id, api_key, transport, host, port))


if __name__ == "__main__":
    main()
