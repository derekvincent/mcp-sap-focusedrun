import os
import pytest
from starlette.testclient import TestClient

os.environ["MCP_ALLOWED_HOSTS"] = "mcp.my-domain.com, mcp-service"

from mcp_sap_focusedrun.server import mcp, SseValidationErrorHandlerMiddleware

@pytest.fixture
def client():
    app = mcp.sse_app()
    app = SseValidationErrorHandlerMiddleware(app)
    return TestClient(app, raise_server_exceptions=True)

def test_allowed_host_custom(client):
    response = client.post("/messages/", headers={"Host": "mcp.my-domain.com", "Content-Type": "application/json"})
    assert response.status_code != 421

def test_allowed_host_localhost(client):
    response = client.post("/messages/", headers={"Host": "127.0.0.1:8000", "Content-Type": "application/json"})
    assert response.status_code != 421

def test_rejected_host(client):
    response = client.post("/messages/", headers={"Host": "malicious-domain.com", "Content-Type": "application/json"})
    assert response.status_code == 421

def test_rejected_host_sse_no_exception(client):
    # This tests that the SSE endpoint correctly responds with 421 
    # without throwing an unhandled ValueError that would fail the TestClient
    response = client.get("/sse", headers={"Host": "malicious-domain.com"})
    assert response.status_code == 421
