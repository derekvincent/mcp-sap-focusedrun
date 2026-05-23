# MCP Server for SAP Focused Run

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/downloads/)
[![Built with FastMCP](https://img.shields.io/badge/Built%20with-FastMCP-blue)](https://github.com/mcp-ai/fastmcp)
> This project provides a Model-Context-Protocol (MCP) server that acts as a bridge between a Large Language Model (LLM) and an SAP Focused Run system. It exposes the Focused Run Landscape Management Database (LMDB) Public API as a set of tools that an LLM can easily query.

## Key Features

- Exposes comprehensive SAP Focused Run endpoints: **Hosts, Systems, Databases, Cloud Tenants, Technical Instances, ABAP Clients, Software Components, and Product Versions**.
- **High-Performance Async Architecture**: Built on `httpx.AsyncClient` with connection pooling and async transport support (`stdio`, `sse`, `streamable-http`).
- **Production Resilience**: Built-in exponential backoff retries for transient SAP API errors (502, 503, 504) and network blips.
- **Identity-Isolated Caching**: 5-minute TTL cache with strict SHA-256 identity isolation, ensuring no data leakage between different tenants or credentials.
- **Security-First Logging**: Sensitive values like usernames and tokens are automatically redacted in logs.
- Packaged as a standard Python application with a command-line entry point.
- Includes predefined MCP Prompts for deep system analysis and landscape discovery.

## Quick Start 

### Prerequisites

- ***[uv](https://docs.astral.sh/uv/)*** installed.
- ***Python 3.13+***
- ***FocusedRun technical user*** with API access to a SAP FocusedRun instance with the following roles ```SAP_FRN_LDB_ALL``` and ```SAP_FRN_LDB_DISP```.
- ***SAP ICF service*** ```sap/frun/landscape/landscape_api``` activated. 
- ***An MCP client*** Cursor, Gemini, Claude Desktop, VS Code with Copilot, etc.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd mcp-sap-focusedrun
    ```

2.  **Install dependencies using uv:**
    This project uses uv for fast Python package management.
    ```bash
    uv sync
    ```

## Usage

The server is configured using environment variables. Create a `.env` file in the root of the project directory and add the following credentials:

```env
API_BASE_URL="https://<your-focused-run-host>/sap/frun/landscape/landscape_api"
SAP_CLIENT="100"
API_USER="YOUR_API_USER"
API_PASSWORD="YOUR_API_PASSWORD"
CUSTOM_HEADERS='{"x-custom-header": "value"}'
```

Or pass the configuration directly in your MCP client config (no .env file needed):
```json
{
  "mcpServers": {
    "sap-focusedrun": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-sap-fucsedrun",
        "run",
        "mcp-sap-focusedrun"
      ],
      "env": {
        "API_BASE_URL": "https://<sap focused run host>/sap/frun/landscape/landscape_api",
        "SAP_CLIENT": "100",
        "API_USER": "YOUR_API_USER",
        "API_PASSWORD": "YOUR_API_PASSWORD",
        "CUSTOM_HEADERS": "{\"x-custom-header\": \"value\"}"
      }
    }
  }
}
```
or via the Docker image:

```bash
docker build -t mcp-sap-focusedrun .
docker run -it --rm --name sap-mcp -p 8000:8000 --env-file .env mcp-sap-focusedrun

```

## Configuration 

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `API_BASE_URL` | X | - | Base url for the Focused Run API |
| `SAP_CLIENT` | X | 100 | SAP FocusedRun Client |
| `API_USER` | X | - | Technical user name |
| `API_PASSWORD` | X | - | Technical user password |
| `CUSTOM_HEADERS` | | - | Optional JSON string of custom HTTP headers |
| `CF_ACCESS_CLIENT_ID` | | - | Cloudflare Access Client ID (optional) |
| `CF_ACCESS_CLIENT_SECRET` | | - | Cloudflare Access Client Secret (optional) |
| `MCP_SERVER_AUTH_TOKEN` | | - | Required for SSE/HTTP transport (raw token value) |
| `TRANSPORT` | | `stdio` | `sse`, `streamable-http`, or `stdio` |
| `PORT` | | 8000 | The port to bind to when running via HTTP |
| `HOST` | | 0.0.0.0 | The host interface to bind to |
| `LOG_LEVEL` | | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CACHE_TTL` | | 300 | API response cache TTL in seconds |
| `CACHE_MAXSIZE` | | 100 | Max number of responses to cache |

## Configuration Overrides (via HTTP Headers)

When running the server in `sse` or `streamable-http` mode, you can dynamically override the configuration for each request. This is ideal for multi-tenant setups.

### Supported Overrides

| Header | Overrides Env Var |
| :--- | :--- |
| `x-api-base-url` | `API_BASE_URL` |
| `x-api-user` | `API_USER` |
| `x-api-password` | `API_PASSWORD` |
| `x-sap-client` | `SAP_CLIENT` |
| `x-cf-access-client-id` | `CF_ACCESS_CLIENT_ID` |
| `x-cf-access-client-secret` | `CF_ACCESS_CLIENT_SECRET` |

> **Precedence:** Header values take absolute precedence over environment variables. If a header is not provided, the server falls back to the default value defined in your environment.

### Authentication

When using HTTP transports, provide your `MCP_SERVER_AUTH_TOKEN` in the `Authorization` header:
`Authorization: Bearer <your_token>`

The server is robust and handles tokens with or without the `Bearer ` prefix gracefully.

## Running Tests

To run the test suite and verify the connection to your SAP Focused Run system, first install `pytest`:
```bash
pip install pytest
```
Then run the tests:
```bash
pytest
```

## Current Issues 

1. The following API's endpoint have not been fully tested: 
   1. ```landscape_api_single_database```
   2. ```landscape_api_technical_instances```
   3. ```landscape_api_abap_clients```