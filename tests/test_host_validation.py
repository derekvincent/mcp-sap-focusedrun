import os
import pytest
from starlette.testclient import TestClient

os.environ["MCP_ALLOWED_HOSTS"] = "mcp.my-domain.com, mcp-service"

from mcp_sap_focusedrun.server import mcp

@pytest.fixture
def client():
    app = mcp.sse_app()
    return TestClient(app)

def test_allowed_host_custom(client):
    response = client.post("/messages/", headers={"Host": "mcp.my-domain.com", "Content-Type": "application/json"})
    assert response.status_code != 421

def test_allowed_host_localhost(client):
    response = client.post("/messages/", headers={"Host": "127.0.0.1:8000", "Content-Type": "application/json"})
    assert response.status_code != 421

def test_rejected_host(client):
    response = client.post("/messages/", headers={"Host": "malicious-domain.com", "Content-Type": "application/json"})
    assert response.status_code == 421
