# SAP Focused Run MCP Server

This project is a Model Context Protocol (MCP) server that provides tools to interact with SAP Focused Run (FRUN) instances. It allows AI models to query landscape information like hosts directly from a Focused Run system.

## Tennents

- If three consecutive fix attempts fail, STOP. Propose: (a) revert, (b) what we know vs don't know, (c) a different approach.
- Do not introduce new libraries, frameworks, or services without asking me first.
- After each feature, update README.md — for someone who'll read it in 3 months having forgotten everything.
- NEVER Implement Workarounds or Band-Aid Solutions - ALWAYS FIX ROOT CAUSE
- Before writing code for any non-trivial change, explain in plain language what you understand the goal is and your planned approach. Wait for my 'go.'
- Require deterministic human confirmation (e.g., Are you sure you want to drop the database?) before executing destructive or production-affecting tasks.
- Require the agent to outline concrete testing steps or provide mock data verification for every code change it authors

## Project Overview

- **Purpose:** Expose SAP Focused Run API capabilities as MCP tools.
- **Main Technologies:**
  - [Python 3.13+](https://www.python.org/)
  - [FastMCP](https://github.com/modelcontextprotocol/python-sdk): For building the MCP server.
  - [httpx](https://www.python-httpx.org/): For making asynchronous HTTP requests to the SAP API.
  - [uv](https://docs.astral.sh/uv/): For project and dependency management.
  - [python-dotenv](https://github.com/theskumar/python-dotenv): For managing environment variables.

## Architecture

- `frun.py`: The entry point for the MCP server. It initializes `FastMCP` and defines the tools available to the AI.
- `focusedrun_client.py`: A specialized client class (`FocusedRun`) that wraps the SAP Focused Run REST API calls. It handles authentication and provides high-level methods for querying hosts by various filters.
- `api_tests.py`: Contains simple test scripts to verify the `FocusedRun` client functionality independently of the MCP server.

## Building and Running

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed.
- A `.env` file with the following variables:
  ```env
  API_BASE_URL=https://<your-frun-host>/sap/bc/srt/rfc/sap/...
  API_KEY=your_api_key
  API_USER=your_username
  API_PASSWORD=your_password
  ```

### Key Commands

- **Install Dependencies:**
  ```bash
  uv sync
  ```
- **Run the MCP Server:**
  ```bash
  uv run frun.py
  ```
- **Run API Client Tests:**
  ```bash
  uv run api_tests.py
  ```

## Development Conventions

- **MCP Tools:** New tools should be added in `frun.py` using the `@mcp.tool()` decorator.
- **API Client:** All SAP-specific logic and REST API interactions should reside in `focusedrun_client.py`.
- **Environment Variables:** Credentials and system-specific configurations must be kept in the `.env` file and never hardcoded.
- **Formatting:** Adhere to standard Python styling. The project uses `uv` for management, so prefer `uv run` for execution.

## Tools Provided

- `get_lmdb_hosts`: Fetches host information from the LMDB.
- `get_lmdb_systems`: Fetches technical systems.
- `get_lmdb_technical_instances`: Fetches technical instances.
- `get_lmdb_databases`: Fetches database instances.
- `get_lmdb_cloud_tenants`: Fetches registered cloud tenants.
- `get_lmdb_installed_software_components`: Fetches installed software components.
- `get_lmdb_installed_product_versions`: Fetches installed product versions.
- `get_lmdb_abap_clients`: Fetches configured ABAP clients.
- `get_lmdb_single_database`: Explicit endpoint for single databases.
