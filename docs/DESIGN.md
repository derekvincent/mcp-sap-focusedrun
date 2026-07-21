# SAP Focused Run MCP Server Design Document

## 1. Overview
The **mcp-sap-focusedrun** project provides a Model-Context-Protocol (MCP) server that acts as a bridge between a Large Language Model (LLM) and the SAP Focused Run Landscape Management Database (LMDB) Public API. It allows AI assistants to securely and efficiently query SAP landscape data (hosts, systems, databases, etc.) to perform analysis and discovery tasks.

Built on top of [FastMCP](https://github.com/mcp-ai/fastmcp), the server translates natural language intent into structured API queries against SAP Focused Run.

## 2. Architecture & Design Principles

### 2.1 High-Performance Async HTTP Client
The core API communication is handled by `httpx.AsyncClient` within the `FocusedRun` class (`src/mcp_sap_focusedrun/focusedrun_client.py`).
- **Connection Pooling:** Configured with sensible limits (`max_keepalive_connections=20`, `max_connections=50`) to handle multiple concurrent LLM requests efficiently.
- **Timeouts:** Hard timeouts (30s read, 10s connect) prevent the server from hanging on unresponsive SAP endpoints.

### 2.2 Resilience & Error Handling
Enterprise APIs can occasionally experience transient network issues or rate limiting. 
- **Exponential Backoff:** The client implements an automatic retry mechanism (up to 3 retries) for transient HTTP errors (502, 503, 504) and underlying `httpx.RequestError` network blips.
- **Redirect Management:** `follow_redirects=False` is explicitly set to detect and handle authentication blocks (e.g., from identity providers like Cloudflare Access) which typically manifest as 301/302 redirects instead of 401s.

### 2.3 Caching Strategy
To reduce load on the SAP LMDB and improve LLM response times, the server uses a `cachetools.TTLCache` (default 5-minute TTL).
- **Identity-Isolated Caching:** A critical security feature. Cache keys are generated using a SHA-256 hash of the `base_url`, `api_user`, `sap_client`, and authentication headers. This strict isolation ensures that in a multi-tenant setup, one tenant cannot accidentally read cached data from another tenant, even if they query the same endpoint with the same parameters.

### 2.4 Security & Logging
- **Data Redaction:** A helper function `__redact` ensures that usernames and other sensitive strings are partially masked in the application logs (e.g., `USE...AME`).
- **DNS Rebinding Protection:** When running over HTTP/SSE, the server integrates FastMCP's `TransportSecuritySettings` to enforce an allowed list of hosts (`MCP_ALLOWED_HOSTS`), preventing DNS rebinding attacks.

### 2.5 Multi-Tenancy & Dynamic Overrides
When deployed via HTTP transports (`sse` or `streamable-http`), the server supports serving multiple SAP environments from a single instance.
- **ASGI Middlewares:** 
  - `HeaderOverrideMiddleware`: Extracts specific `x-` headers (e.g., `x-api-base-url`, `x-api-user`) and stores them in a Python `ContextVar`.
  - The `FocusedRun` client reads this `ContextVar` during request execution, allowing per-request configuration overrides without modifying global state.
- **Authentication:** `BearerAuthMiddleware` enforces token-based authentication (`MCP_SERVER_AUTH_TOKEN`) for HTTP endpoints to secure the MCP connection.

## 3. Tools and Prompts

The server maps the following SAP LMDB Public API endpoints to MCP Tools, using `ToolAnnotations` to mark them as read-only and idempotent:
- `get_lmdb_hosts`: Physical/virtual host machines.
- `get_lmdb_systems`: Technical systems (ABAP, Java, HANA, etc.).
- `get_lmdb_technical_instances`: Application servers and central services.
- `get_lmdb_databases`: Database systems.
- `get_lmdb_cloud_tenants`: SaaS properties and cloud endpoints.
- `get_lmdb_installed_software_components`: Software components and patch levels.
- `get_lmdb_installed_product_versions`: Main product versions.
- `get_lmdb_abap_clients`: Configured clients (e.g., 000, 100).
- `get_lmdb_single_database`: Explicit single database endpoint.
- `find_customer`: (New) Specialized tool for resolving Customer IDs and Names with minimal data transfer.
- `search_lmdb_by_product_version`: (New) Searches customer systems by product version name and filters by environment tier.

### 2.6 Customer Search Architectural Strategy
The `find_customer` tool implements a specialized search strategy to overcome specific limitations of the SAP LMDB Public API:
- **Endpoint Selection:** It utilizes the `landscape_api_installed_product_versions` endpoint as it consistently contains customer metadata across the landscape.
- **Context Efficiency:** To minimize LLM context usage, the tool uses `$select` to restrict the payload to only three fields: `CUSTOMER_NETWORK`, `CUSTOMER_NETWORK_NAME`, and `CUSTOMER_NAME`.
- **Hybrid Search Model:**
    - **Exhaustive Recursive Fetch:** Due to the LMDB API's instability when combining multiple OData `or` filters with parentheses (which often results in HTTP 400 errors), the tool performs a series of paginated requests (using `$skip` and `$top`). It fetches batches of 2,000 records recursively until the end of the data set is reached (or a safety limit of 20,000 is hit).
    - **Client-Side Fuzzy Filtering:** Filtering for `search_query` is performed on the client side across all three customer fields. This ensures that every customer in the landscape is analyzed for a match, regardless of the total landscape size.
    - **Deduplication:** Since the source endpoint returns one record per product version, the tool deduplicates results by `CUSTOMER_NETWORK` before returning them to the LLM.

### 2.7 Product Version Search Architectural Strategy
The `search_lmdb_by_product_version` tool enables searching systems based on their installed products and environment tier:
- **OData Filter Restrictions:** Verification against the SAP Focused Run REST API showed that properties like `PRODUCT_NAME`, `PRODUCT_VERSION`, and `ITADMIN_ROLE` are not filterable at the OData level (returning HTTP 400). However, the page outlines `INST_PRODUCT_VERSION_NAME` as the correct property to filter by product version name.
- **Single-Query Architecture:** The lifecycle role (returned as `ITADMIN_ROLE` or `IT_ADMIN_ROLE` in the product version payload) is filtered client-side directly from the query response, avoiding the latency of a secondary database join/OData query against the systems endpoint.
- **Predefined & Custom Tier Mappings:** Predefined mappings map terms like `DEV`, `QAS`, and `PROD` to standard SAP lifecycle roles (e.g. `Development System`, `Quality Assurance System`, `Production System`). A case-insensitive substring search fallback is implemented to dynamically support custom/future tiers (e.g. `Sandbox`, `Training`, `DR`) without requiring code changes.

**MCP Prompts:**
- `analyze_sap_system`: Guides the LLM to perform a deep-dive analysis of a specific `system_id`.
- `search_customer_landscape`: Guides the LLM to map out the entire footprint for a specific `customer_name`.

## 4. Setup & Configuration

The server is highly configurable via environment variables (`.env` file or native environment).

### 4.1 Transports
The application entry point (`main()` in `server.py`) supports multiple MCP transports based on the `TRANSPORT` environment variable:
- `stdio` (Default): Standard input/output for local desktop clients (Cursor, Claude Desktop).
- `sse` / `streamable-http`: Runs an ASGI Uvicorn server on `HOST`:`PORT` for remote/cloud deployments.

### 4.2 Key Configuration Variables
- `API_BASE_URL`, `SAP_CLIENT`, `API_USER`, `API_PASSWORD`: Core SAP credentials.
- `CUSTOM_HEADERS`: Allows passing static JSON headers required by enterprise proxies.
- `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`: First-class support for Cloudflare Zero Trust environments.

## 5. Testing & Validation Scenarios

Testing is orchestrated via `pytest`. The testing strategy should cover:

### 5.1 Unit Tests
- **Cache Isolation:** Verify that requests with different credentials but identical parameters yield different cache keys and do not leak data.
- **Middleware Logic:** Test that `HeaderOverrideMiddleware` correctly populates `ContextVars` and that `BearerAuthMiddleware` correctly accepts/rejects valid/invalid tokens (with and without the "Bearer " prefix).
- **Retry Logic:** Mock `httpx.AsyncClient.get` to return 503s and verify the exponential backoff triggers before eventually succeeding or failing.

### 5.2 Integration Tests
- **API Connectivity:** End-to-end tests against a mock SAP LMDB API (or a sandbox environment) to verify JSON parsing and client-side pagination (`$top`, `$skip`).
- **Endpoint Coverage:** Ensure all defined MCP tools successfully map to their respective LMDB endpoints and handle empty/null responses gracefully. 

*Note: The `README.md` identifies that endpoints like `landscape_api_single_database`, `landscape_api_technical_instances`, and `landscape_api_abap_clients` require further integration testing validation in real-world environments.*