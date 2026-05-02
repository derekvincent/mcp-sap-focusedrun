# MCP Server for SAP Focused Run

This project provides a Model-Context-Protocol (MCP) server that acts as a bridge between a Large Language Model (LLM) and an SAP Focused Run system. It exposes the Focused Run Landscape Management Database (LMDB) Public API as a set of tools that an LLM can easily query.

## Features

- Exposes comprehensive SAP Focused Run endpoints: **Hosts, Systems, Databases, Cloud Tenants, Technical Instances, ABAP Clients, Software Components, and Product Versions**.
- Lazy, on-demand client initialization.
- Graceful error handling for API and network issues.
- Packaged as a standard Python application with a command-line entry point.
- **Built-in 5-minute TTL caching** to protect the SAP backend from duplicate LLM requests.
- Includes predefined MCP Prompts for deep system analysis and landscape discovery.

## Installation

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

## Configuration

The server is configured using environment variables. Create a `.env` file in the root of the project directory and add the following credentials:

```env
API_BASE_URL="https://<your-focused-run-host>/sap/frun/landscape/landscape_api"
SAP_CLIENT="100"
API_USER="YOUR_API_USER"
API_PASSWORD="YOUR_API_PASSWORD"
```

## Usage

Once installed and configured, you can start the MCP server with the following command:
```bash
uv run mcp-sap-focusedrun
```

## Running Tests

To run the test suite and verify the connection to your SAP Focused Run system, first install `pytest`:
```bash
pip install pytest
```
Then run the tests:
```bash
pytest
```