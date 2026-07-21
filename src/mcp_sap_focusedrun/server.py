import json
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from .focusedrun_client import FocusedRun, request_config_overrides

# Load environment variables
load_dotenv()

# Configure logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

default_tool_annotations = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False
)

# Initialize the MCP server
allowed_hosts_str = os.getenv("MCP_ALLOWED_HOSTS", "")
if allowed_hosts_str:
    allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]
    # Ensure local development hosts are included to prevent breaking local testing
    if not any(h.startswith("localhost") or h.startswith("127.0.0.1") for h in allowed_hosts):
        allowed_hosts.extend(["127.0.0.1:*", "localhost:*"])
    
    security_settings = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=["*"] # Allow all origins, rely on ingress for CORS if needed
    )
    mcp = FastMCP("mcp-sap-focusedrun", transport_security=security_settings)
else:
    mcp = FastMCP("mcp-sap-focusedrun")

# Global variable to hold our client instance
_frun_client: Optional[FocusedRun] = None

class SseValidationErrorHandlerMiddleware:
    """
    ASGI middleware to catch specific ValueError raised by mcp.server.sse when
    HostHeader validation fails, preventing unhandled exception tracebacks in the logs.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            return await self.app(scope, receive, send)
        except ValueError as e:
            if str(e) == "Request validation failed":
                # The response (e.g. 421) has already been sent by connect_sse.
                # We can safely swallow this exception.
                return
            raise

class HeaderOverrideMiddleware:
    """
    ASGI middleware to extract x- headers and populate the request_config_overrides context variable.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            
            overrides = {}
            # Map x- headers to internal override keys
            # Use .get() with bytes since ASGI headers are bytes
            if b"x-api-base-url" in headers:
                overrides["base_url"] = headers[b"x-api-base-url"].decode("utf-8")
            if b"x-api-user" in headers:
                overrides["api_user"] = headers[b"x-api-user"].decode("utf-8")
            if b"x-api-password" in headers:
                overrides["api_password"] = headers[b"x-api-password"].decode("utf-8")
            if b"x-sap-client" in headers:
                overrides["sap_client"] = headers[b"x-sap-client"].decode("utf-8")
            if b"x-cf-access-client-id" in headers:
                overrides["cf_id"] = headers[b"x-cf-access-client-id"].decode("utf-8")
            if b"x-cf-access-client-secret" in headers:
                overrides["cf_secret"] = headers[b"x-cf-access-client-secret"].decode("utf-8")

            if overrides:
                logger.debug(f"Applying header overrides: {list(overrides.keys())}")
                token = request_config_overrides.set(overrides)
                try:
                    return await self.app(scope, receive, send)
                finally:
                    request_config_overrides.reset(token)
            
        return await self.app(scope, receive, send)

class BearerAuthMiddleware:
    """
    ASGI middleware for Bearer token authentication.
    Handles tokens with or without "Bearer " prefix in config or request.
    """
    def __init__(self, app, token: str):
        self.app = app
        # Normalize the expected token: remove "Bearer " if provided in env var
        clean_token = token.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()
        self.expected_token_value = clean_token
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract Authorization header (case-insensitive in logic, lowercase in ASGI bytes)
            auth_header = None
            for key, value in scope.get("headers", []):
                if key.lower() == b"authorization":
                    auth_header = value.decode("utf-8")
                    break
            
            is_authorized = False
            if auth_header:
                # Handle potential doubling or prefixes
                parts = auth_header.split()
                # Most standard: "Bearer <token>"
                if len(parts) >= 2 and parts[0].lower() == "bearer":
                    # We check if the token part matches our expected value
                    if parts[1] == self.expected_token_value:
                        is_authorized = True
                # Fallback: exact match (no prefix in header)
                elif auth_header == self.expected_token_value:
                    is_authorized = True

            if not is_authorized:
                logger.warning(f"Unauthorized access attempt. Path: {scope.get('path')}")
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", b"25")
                    ]
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"error": "Unauthorized"}',
                    "more_body": False
                })
                return
                
        return await self.app(scope, receive, send)

def get_focusedrun_client() -> FocusedRun:
    """Lazy initialization of the FocusedRun client."""
    global _frun_client
    if _frun_client is None:
        logger.info("Initializing SAP Focused Run client...")
        
        # Collect custom headers
        custom_headers = {}
        
        custom_headers_raw = os.getenv("CUSTOM_HEADERS")
        if custom_headers_raw:
            try:
                # Handle cases where the environment might already provide a dict (e.g. via certain config loaders)
                if isinstance(custom_headers_raw, dict):
                    custom_headers.update(custom_headers_raw)
                else:
                    custom_headers.update(json.loads(custom_headers_raw))
                logger.info("Loaded custom headers from CUSTOM_HEADERS environment variable.")
            except (json.JSONDecodeError, TypeError):
                logger.error("Failed to parse CUSTOM_HEADERS environment variable. Expected valid JSON object.")

        # Cloudflare Access headers from ENV (Default fallback)
        cf_id = os.getenv("CF_ACCESS_CLIENT_ID")
        cf_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")
        if cf_id:
            custom_headers["CF-Access-Client-Id"] = cf_id
        if cf_secret:
            custom_headers["CF-Access-Client-Secret"] = cf_secret

        if custom_headers:
            logger.info(f"Loaded {len(custom_headers)} custom headers from environment.")

        _frun_client = FocusedRun(
            base_url=os.getenv("API_BASE_URL", ""),
            sap_client=os.getenv("SAP_CLIENT", "100"),
            api_key=os.getenv("API_KEY", ""),
            api_user=os.getenv("API_USER", ""),
            api_password=os.getenv("API_PASSWORD", ""),
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
            cache_maxsize=int(os.getenv("CACHE_MAXSIZE", "100")),
            additional_headers=custom_headers
        )
    return _frun_client

@mcp.tool(annotations=default_tool_annotations)
async def find_customer(
    customer_network_id: Optional[str] = None,
    search_query: Optional[str] = None,
    top: int = 20,
    skip: int = 0
) -> dict:
    """
    Find customer information (ID, Network Name, Customer Name).
    Use this tool when you need to resolve a customer name to a CUSTOMER_NETWORK ID or vice versa.
    This tool provides a minimal data set to reduce context overhead.
    It deduplicates results from the product versions landscape.
    - If customer_network_id is provided, it attempts a direct hit first.
    - search_query performs a fuzzy search across CUSTOMER_NAME, CUSTOMER_NETWORK, and CUSTOMER_NETWORK_NAME.
    """
    logger.info(f"Tool 'find_customer' invoked | id={customer_network_id}, query={search_query}, top={top}, skip={skip}")
    client = get_focusedrun_client()
    
    return await client.get_customers(
        customer_network_id=customer_network_id,
        search_query=search_query,
        top=top,
        skip=skip
    )

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_hosts(
    hostnames: Optional[List[str]] = None,
    customer_names: Optional[List[str]] = None,
    customer_networks: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve physical or virtual host machines from the SAP Focused Run LMDB.
    Use this tool when the user asks about servers, hosts, operating systems, or datacenters.
    This is a read-only operation.
    Filters can be combined (e.g. hostnames AND customer_names).
    Use top and skip for pagination. Use select_fields to limit the returned columns (e.g., ['HOST_NAME', 'OS_NAME']).
    """
    logger.info(f"Tool 'get_lmdb_hosts' invoked | hostnames={hostnames}, customer={customer_names}, net={customer_networks}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_hosts(hostnames=hostnames, customer_names=customer_names, customer_networks=customer_networks, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_systems(
    system_ids: Optional[List[str]] = None,
    customer_names: Optional[List[str]] = None,
    system_types: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve technical systems (e.g., SAP ABAP, Java, or Cloud services) from the SAP Focused Run LMDB.
    Use this tool to find a system's EXTENDED_SID, which is often required as an input for other tools.
    This is a read-only operation.
    Valid system_types include (but are not limited to):
      - 'ABAP':	Application Server ABAP
      - 'ATC':	Apache Tomcat Server
      - 'BOBJ':	SAP BusinessObjects Cluster
      - 'DBSYSTEM':	Database System
      - 'DIAGNAGENT':	Diagnostics Agent
      - 'EXT_SRV':	External Service
      - 'HANADB':	SAP HANA Database
      - 'IS_EM':	Introscope Enterprise Manager (Standalone)
      - 'IS_MOM':	Introscope Enterprise Manager (Cluster)
      - 'JAVA':	Application Server Java
      - 'LIVE_CACHE':	SAP liveCache
      - 'MDM':	SAP NetWeaver Master Data Management Server
      - 'MSIISINST':	Microsoft Internet Information Services
      - 'MS_.NET':	.NET System
      - 'SUP':	SAP Mobile Platform
      - 'TREX':	TREX System
      - 'UNSP3TIER':	Unspecific 3-Tier System
      - 'UNSPAPP':	Unspecific Standalone Application System
      - 'UNSPECIFIC':	Unspecific Cluster System
      - 'WEBDISP':	SAP Web Dispatcher
      - 'WEBSPHERE':	IBM WebSphere Application Server
    Filters can be combined. 
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_systems' invoked | system_ids={system_ids}, customer={customer_names}, types={system_types}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_systems(system_ids=system_ids, customer_names=customer_names, system_types=system_types, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_technical_instances(
    system_ids: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve specific technical instances running on hosts for a given SAP system.
    Use this tool when asked about application servers, central services, or specific instances.
    This is a read-only operation.
    Filters can be combined.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_technical_instances' invoked | system_ids={system_ids}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_technical_instances(system_ids=system_ids, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_databases(
    system_ids: Optional[List[str]] = None,
    customer_names: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve database systems from the SAP Focused Run LMDB.
    Use this tool when the user asks about database tenants, DB versions, or database hosts.
    This is a read-only operation.
    Filters can be combined.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_databases' invoked | system_ids={system_ids}, customer={customer_names}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_databases(system_ids=system_ids, customer_names=customer_names, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_cloud_tenants(
    tenant_ids: Optional[List[str]] = None,
    customer_names: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve registered cloud tenants and services from the SAP Focused Run LMDB.
    Use this tool when the user asks about SaaS properties, BTP, or cloud endpoints.
    This is a read-only operation.
    Filters can be combined.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_cloud_tenants' invoked | tenant_ids={tenant_ids}, customer={customer_names}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_cloud_tenants(tenant_ids=tenant_ids, customer_names=customer_names, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_installed_software_components(
    system_ids: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve the software components installed on a specific SAP system.
    Use this tool to check component versions, support packages (SP), or patch levels.
    This is a read-only operation.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_installed_software_components' invoked | system_ids={system_ids}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None: kwargs["$top"] = top
    if skip is not None: kwargs["$skip"] = skip
    if select_fields: kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_installed_software_components(system_ids=system_ids, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_installed_product_versions(
    system_ids: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve the main product versions installed on a specific SAP system.
    Use this tool to determine what high-level SAP products (e.g., S/4HANA) are running.
    This is a read-only operation.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_installed_product_versions' invoked | system_ids={system_ids}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None: kwargs["$top"] = top
    if skip is not None: kwargs["$skip"] = skip
    if select_fields: kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_installed_product_versions(system_ids=system_ids, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_abap_clients(
    system_ids: Optional[List[str]] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Retrieve the configured ABAP clients (e.g., 000, 100) for a specific SAP ABAP system.
    Use this tool when the user needs to know what clients exist in a system.
    This is a read-only operation.
    Use top and skip for pagination. Use select_fields to limit the returned columns.
    """
    logger.info(f"Tool 'get_lmdb_abap_clients' invoked | system_ids={system_ids}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None: kwargs["$top"] = top
    if skip is not None: kwargs["$skip"] = skip
    if select_fields: kwargs["$select"] = ",".join(select_fields)
        
    return await client.get_abap_clients(system_ids=system_ids, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_single_database() -> dict:
    """
    Explicitly retrieve the single database endpoint from SAP Focused Run LMDB.
    This is a read-only operation.
    (Note: If this returns HTTP 400 in your environment, use get_lmdb_databases instead).
    """
    logger.info("Tool 'get_lmdb_single_database' invoked")
    client = get_focusedrun_client()
    return await client.get_single_database()

@mcp.tool(annotations=default_tool_annotations)
async def search_lmdb_by_product_version(
    product_version_name: str,
    customer_name: Optional[str] = None,
    customer_network: Optional[str] = None,
    tier: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    select_fields: Optional[List[str]] = None
) -> dict:
    """
    Search for customer systems in the LMDB by product version name.
    Supports wildcard queries (e.g. 'SAP ERP' or '*SAP ERP*').
    Allows optional customer name and customer network filtering.
    Performs case-insensitive client-side filtering on the environment 'tier' parameter
    (e.g., 'DEV' or 'Development', 'QAS' or 'Quality' or 'Test', 'PROD' or 'Production',
    or custom tiers like 'Sandbox', 'Training', 'DR').
    This is a read-only operation.
    """
    logger.info(
        f"Tool 'search_lmdb_by_product_version' invoked | "
        f"product={product_version_name}, customer={customer_name}, "
        f"network={customer_network}, tier={tier}"
    )
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None: kwargs["$top"] = top
    if skip is not None: kwargs["$skip"] = skip
    if select_fields: kwargs["$select"] = ",".join(select_fields)
        
    return await client.search_by_product_version(
        product_version_name=product_version_name,
        customer_name=customer_name,
        customer_network=customer_network,
        tier=tier,
        **kwargs
    )

# MCP Prompts
@mcp.prompt()
def analyze_sap_system(system_id: str) -> str:
    """Generate a prompt to deeply analyze a specific SAP system."""
    return (
        f"Please perform a deep analysis of the SAP system with ID '{system_id}'.\n"
        f"1. Fetch the basic system details.\n"
        f"2. Identify all technical instances and databases attached to this system.\n"
        f"3. List the primary installed product versions and software components.\n"
        f"Provide a comprehensive, formatted landscape architecture summary based on this data."
    )

@mcp.prompt()
def search_customer_landscape(customer_name: str) -> str:
    """Generate a prompt to map out a customer's entire footprint."""
    return (
        f"Please map out the footprint for the customer '{customer_name}'.\n"
        f"Find all their hosts, systems, databases, and cloud tenants, and provide a structured inventory."
    )

def main():
    """Entry point for the application script"""
    transport = os.getenv("TRANSPORT", "stdio").lower()
    if transport in ["sse", "streamable-http"]:
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "0.0.0.0")
        
        # Get the underlying Starlette app from FastMCP
        if transport == "sse":
            app = mcp.sse_app()
        else:
            app = mcp.streamable_http_app()
        
        # Apply middlewares (Outer to Inner)
        
        # 1. Bearer Auth Middleware (Outer)
        auth_token = os.getenv("MCP_SERVER_AUTH_TOKEN")
        if auth_token:
            logger.info("Authentication enabled. Bearer token required for SSE endpoints.")
            app = BearerAuthMiddleware(app, auth_token)
            
        # 2. Header Override Middleware (Inner)
        app = HeaderOverrideMiddleware(app)
        
        # 3. Error Handling Middleware (Inner-most custom)
        app = SseValidationErrorHandlerMiddleware(app)
        
        logger.info(f"Starting MCP server on {host}:{port} via {transport}")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
