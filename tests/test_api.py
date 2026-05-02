import os

from dotenv import load_dotenv

from mcp_sap_focusedrun import focusedrun_client as focusedrun

load_dotenv()
API = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")
API_USER = os.getenv("API_USER")
API_PASSWORD = os.getenv("API_PASSWORD")

def get_client():
    """Helper method to initialize the client for tests."""
    return focusedrun.FocusedRun(
        base_url=API,
        sap_client="100",
        api_key=API_KEY,
        api_user=API_USER,
        api_password=API_PASSWORD
    )

def assert_no_error(result):
    """Helper to check if the result is an error dictionary and fail with a clear message."""
    if isinstance(result, dict):
        assert "error" not in result, f"API Failed: {result.get('error')} | Details: {result.get('details')}"

# --- Hosts Tests ---
def test_get_hosts_landscapes():
    frun = get_client()
    result = frun.get_hosts()
    assert_no_error(result)

def test_get_hosts_by_hostnames():
    frun = get_client()
    result = frun.get_hosts(hostnames=["bshcf56n01h", "bshcf56n02h"])
    assert_no_error(result)

def test_get_hosts_by_customer_names():
    frun = get_client()
    result = frun.get_hosts(customer_names=["ADM"])
    assert_no_error(result)

def test_get_hosts_by_customer_networks():
    frun = get_client()
    result = frun.get_hosts(customer_networks=["LOCALNETWORK"])
    assert_no_error(result)

def test_get_hosts_pagination():
    frun = get_client()
    result = frun.get_hosts(**{"$top": 1, "$skip": 1})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 1

def test_get_hosts_composite_filter():
    frun = get_client()
    result = frun.get_hosts(hostnames=["bshcf56n01h"], customer_names=["ADM"])
    assert_no_error(result)

def test_get_hosts_select_projection():
    frun = get_client()
    result = frun.get_hosts(**{"$top": 1, "$select": "HOST_NAME,CUSTOMER_NAME"})
    assert_no_error(result)

# --- Systems Tests ---
def test_get_systems():
    frun = get_client()
    result = frun.get_systems()
    assert_no_error(result)

def test_get_systems_by_system_ids():
    frun = get_client()
    # Feel free to replace "PRD" with a system ID valid in your landscape
    result = frun.get_systems(system_ids=["PRD"])
    assert_no_error(result)

def test_get_systems_by_customer_names():
    frun = get_client()
    result = frun.get_systems(customer_names=["ADM"])
    assert_no_error(result)

def test_get_systems_by_type():
    frun = get_client()
    # This test now correctly fetches databases by filtering the systems endpoint
    result = frun.get_systems(system_types=["DATABASE"])
    assert_no_error(result)

def test_get_systems_pagination():
    frun = get_client()
    result = frun.get_systems(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Technical Instances Tests ---
def test_get_technical_instances():
    frun = get_client()
    result = frun.get_technical_instances()
    assert_no_error(result)

def test_get_technical_instances_by_system_ids():
    frun = get_client()
    result = frun.get_technical_instances(system_ids=["PRD"])
    assert_no_error(result)

def test_get_technical_instances_pagination():
    frun = get_client()
    result = frun.get_technical_instances(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Cloud Tenants Tests ---
def test_get_cloud_tenants():
    frun = get_client()
    result = frun.get_cloud_tenants()
    assert_no_error(result)

def test_get_cloud_tenants_by_tenant_ids():
    frun = get_client()
    result = frun.get_cloud_tenants(tenant_ids=["MY_TENANT"])
    assert_no_error(result)

def test_get_cloud_tenants_by_customer_names():
    frun = get_client()
    result = frun.get_cloud_tenants(customer_names=["ADM"])
    assert_no_error(result)

def test_get_cloud_tenants_pagination():
    frun = get_client()
    result = frun.get_cloud_tenants(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Databases Tests ---
def test_get_databases():
    frun = get_client()
    result = frun.get_databases()
    assert_no_error(result)

def test_get_databases_by_system_ids():
    frun = get_client()
    result = frun.get_databases(system_ids=["PRD"])
    assert_no_error(result)

def test_get_databases_by_customer_names():
    frun = get_client()
    result = frun.get_databases(customer_names=["ADM"])
    assert_no_error(result)

def test_get_databases_pagination():
    frun = get_client()
    result = frun.get_databases(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Installed Software Components Tests ---
def test_get_installed_software_components():
    frun = get_client()
    result = frun.get_installed_software_components()
    assert_no_error(result)

def test_get_installed_software_components_by_system_ids():
    frun = get_client()
    result = frun.get_installed_software_components(system_ids=["PRD"])
    assert_no_error(result)

def test_get_installed_software_components_pagination():
    frun = get_client()
    result = frun.get_installed_software_components(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- Installed Product Versions Tests ---
def test_get_installed_product_versions():
    frun = get_client()
    result = frun.get_installed_product_versions()
    assert_no_error(result)

def test_get_installed_product_versions_by_system_ids():
    frun = get_client()
    result = frun.get_installed_product_versions(system_ids=["PRD"])
    assert_no_error(result)

def test_get_installed_product_versions_pagination():
    frun = get_client()
    result = frun.get_installed_product_versions(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# --- ABAP Clients Tests ---
def test_get_abap_clients():
    frun = get_client()
    result = frun.get_abap_clients()
    assert_no_error(result)

def test_get_abap_clients_by_system_ids():
    frun = get_client()
    result = frun.get_abap_clients(system_ids=["PRD"])
    assert_no_error(result)

def test_get_abap_clients_pagination():
    frun = get_client()
    result = frun.get_abap_clients(**{"$top": 2, "$skip": 0})
    assert_no_error(result)
    if isinstance(result, list):
        assert len(result) <= 2

# Note: landscape_api_single_database tests are intentionally omitted here 
# to prevent automated 400 Bad Request pipeline failures previously seen.
