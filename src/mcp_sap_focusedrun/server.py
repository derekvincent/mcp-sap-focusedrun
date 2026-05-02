import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .focusedrun_client import FocusedRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
        load_dotenv()
        _frun_client = FocusedRun(
            base_url=os.getenv("API_BASE_URL", ""),
            sap_client=os.getenv("SAP_CLIENT", "100"),
            api_key=os.getenv("API_KEY", ""),
            api_user=os.getenv("API_USER", ""),
            api_password=os.getenv("API_PASSWORD", "")
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
    instance_names: Optional[List[str]] = None,
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
    logger.info(f"Tool 'get_lmdb_technical_instances' invoked | system_ids={system_ids}, instances={instance_names}, select={select_fields}")
    client = get_focusedrun_client()
    
    kwargs = {}
    if top is not None:
        kwargs["$top"] = top
    if skip is not None:
        kwargs["$skip"] = skip
    if select_fields:
        kwargs["$select"] = ",".join(select_fields)
        
    return client.get_technical_instances(system_ids=system_ids, instance_names=instance_names, **kwargs)

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
        # We monkeypatch uvicorn.Config to force binding to 0.0.0.0 for Docker compatibility.
        original_config_init = uvicorn.Config.__init__
        def patched_config_init(self, *args, **kwargs):
            kwargs["host"] = "0.0.0.0"
            kwargs["port"] = port
            original_config_init(self, *args, **kwargs)
        uvicorn.Config.__init__ = patched_config_init
        
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
