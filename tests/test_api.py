import os
import pytest
from dotenv import load_dotenv
from mcp_sap_focusedrun import focusedrun_client as focusedrun

load_dotenv()

API = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
API_USER = os.getenv("API_USER")
API_PASSWORD = os.getenv("API_PASSWORD")

# Mark all tests in this file as async for anyio
pytestmark = pytest.mark.anyio

def get_client():
    """Helper method to initialize the client for tests."""
    return focusedrun.FocusedRun(
        base_url=API,
        sap_client="100",
        api_key=API_KEY,
        api_user=API_USER,
        api_password=API_PASSWORD
    )

@pytest.fixture
async def frun():
    """Async fixture to manage client lifecycle and connection cleanup."""
    client = get_client()
    yield client
    await client.close()

def assert_no_error(result):
    """Helper to check if the result is an error dictionary and fail with a clear message."""
    if isinstance(result, dict):
        assert "error" not in result, f"API Failed: {result.get('error')} | Details: {result.get('details')}"

# --- Hosts Tests ---
async def test_get_hosts_landscapes(frun):
    result = await frun.get_hosts()
    assert_no_error(result)

async def test_get_hosts_by_hostnames(frun):
    result = await frun.get_hosts(hostnames=["bshcf56n01h", "bshcf56n02h"])
    assert_no_error(result)

async def test_get_hosts_by_customer_names(frun):
    result = await frun.get_hosts(customer_names=["ADM"])
    assert_no_error(result)

async def test_get_hosts_by_customer_networks(frun):
    result = await frun.get_hosts(customer_networks=["LOCALNETWORK"])
    assert_no_error(result)

async def test_get_hosts_pagination(frun):
    result = await frun.get_hosts(**{"$top": 1, "$skip": 1})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 1

async def test_get_hosts_composite_filter(frun):
    result = await frun.get_hosts(hostnames=["bshcf56n01h"], customer_names=["ADM"])
    assert_no_error(result)

async def test_get_hosts_select_projection(frun):
    result = await frun.get_hosts(**{"$top": 1, "$select": "HOST_NAME,CUSTOMER_NAME"})
    assert_no_error(result)

# --- Systems Tests ---
async def test_get_systems(frun):
    result = await frun.get_systems()
    assert_no_error(result)

async def test_get_systems_by_system_ids(frun):
    result = await frun.get_systems(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_systems_by_customer_names(frun):
    result = await frun.get_systems(customer_names=["ADM"])
    assert_no_error(result)

async def test_get_systems_by_type(frun):
    result = await frun.get_systems(system_types=["DATABASE"])
    assert_no_error(result)

async def test_get_systems_pagination(frun):
    result = await frun.get_systems(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Technical Instances Tests ---
async def test_get_technical_instances(frun):
    result = await frun.get_technical_instances()
    assert_no_error(result)

async def test_get_technical_instances_by_system_ids(frun):
    result = await frun.get_technical_instances(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_technical_instances_pagination(frun):
    result = await frun.get_technical_instances(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Cloud Tenants Tests ---
async def test_get_cloud_tenants(frun):
    result = await frun.get_cloud_tenants()
    assert_no_error(result)

async def test_get_cloud_tenants_by_tenant_ids(frun):
    result = await frun.get_cloud_tenants(tenant_ids=["MY_TENANT"])
    assert_no_error(result)

async def test_get_cloud_tenants_by_customer_names(frun):
    result = await frun.get_cloud_tenants(customer_names=["ADM"])
    assert_no_error(result)

async def test_get_cloud_tenants_pagination(frun):
    result = await frun.get_cloud_tenants(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Databases Tests ---
async def test_get_databases(frun):
    result = await frun.get_databases()
    assert_no_error(result)

async def test_get_databases_by_system_ids(frun):
    result = await frun.get_databases(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_databases_by_customer_names(frun):
    result = await frun.get_databases(customer_names=["ADM"])
    assert_no_error(result)

async def test_get_databases_pagination(frun):
    result = await frun.get_databases(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Installed Software Components Tests ---
async def test_get_installed_software_components(frun):
    result = await frun.get_installed_software_components()
    assert_no_error(result)

async def test_get_installed_software_components_by_system_ids(frun):
    result = await frun.get_installed_software_components(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_installed_software_components_pagination(frun):
    result = await frun.get_installed_software_components(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Installed Product Versions Tests ---
async def test_get_installed_product_versions(frun):
    result = await frun.get_installed_product_versions()
    assert_no_error(result)

async def test_get_installed_product_versions_by_system_ids(frun):
    result = await frun.get_installed_product_versions(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_installed_product_versions_pagination(frun):
    result = await frun.get_installed_product_versions(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- ABAP Clients Tests ---
async def test_get_abap_clients(frun):
    result = await frun.get_abap_clients()
    assert_no_error(result)

async def test_get_abap_clients_by_system_ids(frun):
    result = await frun.get_abap_clients(system_ids=["PRD"])
    assert_no_error(result)

async def test_get_abap_clients_pagination(frun):
    result = await frun.get_abap_clients(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Search by Product Version Tests ---
async def test_search_by_product_version_empty(frun):
    # Tests that the endpoint compiles the query and returns successfully
    result = await frun.search_by_product_version(product_version_name="DUMMY_PRODUCT_NAME_XYZ")
    assert isinstance(result, list)
    assert len(result) == 0

async def test_search_by_product_version_tier_filtering(monkeypatch):
    # Prepare dummy client and mock _make_request to verify local tier filtering mappings
    frun_client = get_client()
    
    mock_payload = [
        {"EXTENDED_SID": "SYS1", "INST_PRODUCT_VERSION_NAME": "SAP ERP 6.0", "ITADMIN_ROLE": "Production System"},
        {"EXTENDED_SID": "SYS2", "INST_PRODUCT_VERSION_NAME": "SAP ERP 6.0", "ITADMIN_ROLE": "Development System"},
        {"EXTENDED_SID": "SYS3", "INST_PRODUCT_VERSION_NAME": "SAP ERP 6.0", "ITADMIN_ROLE": "Quality Assurance System"},
        {"EXTENDED_SID": "SYS4", "INST_PRODUCT_VERSION_NAME": "SAP ERP 6.0", "ITADMIN_ROLE": "Sandbox Environment"},
        {"EXTENDED_SID": "SYS5", "INST_PRODUCT_VERSION_NAME": "SAP ERP 6.0", "IT_ADMIN_ROLE": "DR System"}, # Tests IT_ADMIN_ROLE fallback
    ]
    
    async def mock_make_request(endpoint, **kwargs):
        return mock_payload
        
    monkeypatch.setattr(frun_client, "_make_request", mock_make_request)
    
    # 1. Test PROD mapping
    prod_results = await frun_client.search_by_product_version("SAP ERP 6.0", tier="PROD")
    assert len(prod_results) == 1
    assert prod_results[0]["EXTENDED_SID"] == "SYS1"
    
    # 2. Test DEV mapping
    dev_results = await frun_client.search_by_product_version("SAP ERP 6.0", tier="Development")
    assert len(dev_results) == 1
    assert dev_results[0]["EXTENDED_SID"] == "SYS2"
    
    # 3. Test QAS mapping
    qas_results = await frun_client.search_by_product_version("SAP ERP 6.0", tier="QAS")
    assert len(qas_results) == 1
    assert qas_results[0]["EXTENDED_SID"] == "SYS3"
    
    # 4. Test custom Sandbox mapping
    sandbox_results = await frun_client.search_by_product_version("SAP ERP 6.0", tier="Sandbox")
    assert len(sandbox_results) == 1
    assert sandbox_results[0]["EXTENDED_SID"] == "SYS4"
    
    # 5. Test custom DR mapping using IT_ADMIN_ROLE
    dr_results = await frun_client.search_by_product_version("SAP ERP 6.0", tier="dr")
    assert len(dr_results) == 1
    assert dr_results[0]["EXTENDED_SID"] == "SYS5"
    
    await frun_client.close()

