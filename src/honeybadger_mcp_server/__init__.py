import logging
import sys

import click

from .server import serve


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
@click.option("-v", "--verbose", count=True)
def main(api_key: str | None, project_id: str | None, verbose: bool) -> None:
    """MCP Honeybadger Server - Honeybadger API functionality for MCP"""
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

    asyncio.run(serve(project_id, api_key))


if __name__ == "__main__":
    main()
