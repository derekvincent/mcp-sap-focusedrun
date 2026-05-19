import logging
import os
import json
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .focusedrun_client import FocusedRun

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
mcp = FastMCP("mcp-sap-focusedrun")

# Global variable to hold our client instance
_frun_client: Optional[FocusedRun] = None

def get_focusedrun_client() -> FocusedRun:
    """Lazy initialization of the FocusedRun client."""
    global _frun_client
    if _frun_client is None:
        logger.info("Initializing SAP Focused Run client...")
        
        # Parse custom headers if provided
        custom_headers = {}
        custom_headers_json = os.getenv("CUSTOM_HEADERS")
        if custom_headers_json:
            try:
                custom_headers = json.loads(custom_headers_json)
                logger.info(f"Loaded {len(custom_headers)} custom headers from environment.")
            except json.JSONDecodeError:
                logger.error("Failed to parse CUSTOM_HEADERS environment variable. Expected valid JSON.")

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
        
    return client.get_hosts(hostnames=hostnames, customer_names=customer_names, customer_networks=customer_networks, **kwargs)

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
        
    return client.get_systems(system_ids=system_ids, customer_names=customer_names, system_types=system_types, **kwargs)

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
        
    return client.get_technical_instances(system_ids=system_ids, **kwargs)

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
        
    return client.get_databases(system_ids=system_ids, customer_names=customer_names, **kwargs)

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
        
    return client.get_cloud_tenants(tenant_ids=tenant_ids, customer_names=customer_names, **kwargs)

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
        
    return client.get_installed_software_components(system_ids=system_ids, **kwargs)

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
        
    return client.get_installed_product_versions(system_ids=system_ids, **kwargs)

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
        
    return client.get_abap_clients(system_ids=system_ids, **kwargs)

@mcp.tool(annotations=default_tool_annotations)
async def get_lmdb_single_database() -> dict:
    """
    Explicitly retrieve the single database endpoint from SAP Focused Run LMDB.
    This is a read-only operation.
    (Note: If this returns HTTP 400 in your environment, use get_lmdb_databases instead).
    """
    logger.info("Tool 'get_lmdb_single_database' invoked")
    client = get_focusedrun_client()
    return client.get_single_database()

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
        
        # FastMCP's SSE transport defaults to 127.0.0.1.
        # We monkeypatch uvicorn.Config to force binding to 0.0.0.0 and optionally inject ASGI auth middleware.
        original_config_init = uvicorn.Config.__init__
        def patched_config_init(self, app, *args, **kwargs):
            kwargs["host"] = "0.0.0.0"
            kwargs["port"] = port
            
            auth_token = os.getenv("MCP_SERVER_AUTH_TOKEN")
            if auth_token:
                logger.info("Authentication enabled. Bearer token required for SSE endpoints.")
                class BearerAuthMiddleware:
                    def __init__(self, app):
                        self.app = app
                        self.token = f"Bearer {auth_token}".encode("utf-8")
                    
                    async def __call__(self, scope, receive, send):
                        if scope["type"] == "http":
                            headers = dict(scope.get("headers", []))
                            if headers.get(b"authorization") != self.token:
                                await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"content-length", b"25")]})
                                await send({"type": "http.response.body", "body": b'{"error": "Unauthorized"}', "more_body": False})
                                return
                        return await self.app(scope, receive, send)
                app = BearerAuthMiddleware(app)
            
            original_config_init(self, app, *args, **kwargs)
        uvicorn.Config.__init__ = patched_config_init
        
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
