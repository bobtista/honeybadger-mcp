# Honeybadger MCP Server

A Model Context Protocol (MCP) server implementation for interacting with the Honeybadger API. This server allows AI agents to fetch and analyze error data from your Honeybadger projects.

## Overview

This MCP server provides a bridge between AI agents and the Honeybadger error monitoring service. It follows the best practices laid out by Anthropic for building MCP servers, allowing seamless integration with any MCP-compatible client.

## Features

The server provides two essential tools for interacting with Honeybadger:

1. **`list_faults`**: List and filter faults from your Honeybadger project
2. **`get_fault_details`**: Get detailed information about specific faults

## Prerequisites

- Python 3.12+
- Honeybadger API key and Project ID
- Docker if running the MCP server as a container (recommended)

## Installation

### Using uv

1. Install uv if you don't have it:

   ```bash
   pip install uv
   ```

2. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/honeybadger-mcp.git
   cd honeybadger-mcp
   ```

3. Install dependencies:

   ```bash
   uv pip install -e .
   ```

4. Create a `.env` file:
   ```bash
   cp .env.example .env
   ```

### Using Docker (Recommended)

1. Build the Docker image:

   ```bash
   docker build -t honeybadger/mcp --build-arg PORT=8050 .
   ```

2. Create a `.env` file and configure your environment variables

## Configuration

The following environment variables need to be configured:

| Variable                 | Description                                | Required                   |
| ------------------------ | ------------------------------------------ | -------------------------- |
| `HONEYBADGER_API_KEY`    | Your Honeybadger API key                   | Yes                        |
| `HONEYBADGER_PROJECT_ID` | Your Honeybadger project ID                | Yes                        |
| `TRANSPORT`              | Transport protocol (sse or stdio)          | No (defaults to sse)       |
| `HOST`                   | Host to bind to when using SSE transport   | No (defaults to 127.0.0.1) |
| `PORT`                   | Port to listen on when using SSE transport | No (defaults to 8050)      |
| `LOG_LEVEL`              | Logging level (INFO, DEBUG, etc.)          | No (defaults to INFO)      |

## Running the Server

### Using uv

#### SSE Transport (Default)

```bash
# Set TRANSPORT=sse in .env (or omit for default) then:
uv run src/honeybadger_mcp_server/server.py
```

The server will start as an API endpoint that you can connect to with the configuration shown below.

#### Stdio Transport

```bash
# Set TRANSPORT=stdio in .env then:
uv run src/honeybadger_mcp_server/server.py
```

### Using Docker

#### SSE Transport (Default)

```bash
docker run --env-file .env -p 8050:8050 honeybadger/mcp
```

#### Stdio Transport

With stdio, the MCP client itself can spin up the MCP server container, so nothing to run at this point.

## Integration with MCP Clients

### SSE Configuration

Once you have the server running with SSE transport, you can connect to it using this configuration:

```json
{
  "mcpServers": {
    "honeybadger": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

### Python with Stdio Configuration

```json
{
  "mcpServers": {
    "honeybadger": {
      "command": "your/path/to/honeybadger-mcp/.venv/Scripts/python.exe",
      "args": [
        "your/path/to/honeybadger-mcp/src/honeybadger_mcp_server/server.py"
      ],
      "env": {
        "TRANSPORT": "stdio",
        "HONEYBADGER_API_KEY": "YOUR-API-KEY",
        "HONEYBADGER_PROJECT_ID": "YOUR-PROJECT-ID"
      }
    }
  }
}
```

### Docker with Stdio Configuration

```json
{
  "mcpServers": {
    "honeybadger": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "TRANSPORT",
        "-e",
        "HONEYBADGER_API_KEY",
        "-e",
        "HONEYBADGER_PROJECT_ID",
        "honeybadger/mcp"
      ],
      "env": {
        "TRANSPORT": "stdio",
        "HONEYBADGER_API_KEY": "YOUR-API-KEY",
        "HONEYBADGER_PROJECT_ID": "YOUR-PROJECT-ID"
      }
    }
  }
}
```

## Tool Usage Examples

### List Faults

```python
result = await client.call_tool("list_faults", {
    "q": "RuntimeError",  # Optional search term
    "limit": 10,         # Max 25 results
    "order": "recent"    # 'recent' or 'frequent'
})
```

### Get Fault Details

```python
result = await client.call_tool("get_fault_details", {
    "fault_id": "abc123",
    "limit": 5  # Number of notices to return (max 25)
})
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
