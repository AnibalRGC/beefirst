"""
Integration tests for OpenAPI documentation.

Verifies OpenAPI schema is correctly generated for all endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for the application."""
    return TestClient(app)


class TestOpenAPISchema:
    """Tests for OpenAPI schema generation."""

    def test_openapi_schema_accessible(self, client: TestClient) -> None:
        """OpenAPI schema is accessible at /openapi.json."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_openapi_title_and_description(self, client: TestClient) -> None:
        """OpenAPI schema has correct title and description."""
        response = client.get("/openapi.json")
        schema = response.json()
        assert schema["info"]["title"] == "beefirst"
        assert "Trust State Machine" in schema["info"]["description"]
        assert schema["info"]["version"] == "0.1.0"

    def test_v1_register_endpoint_in_schema(self, client: TestClient) -> None:
        """POST /v1/register endpoint is documented in schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/v1/register" in schema["paths"]
        register = schema["paths"]["/v1/register"]
        assert "post" in register
        assert register["post"]["summary"] == "Register a new user"

    def test_v1_activate_endpoint_in_schema(self, client: TestClient) -> None:
        """POST /v1/activate endpoint is documented in schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "/v1/activate" in schema["paths"]
        activate = schema["paths"]["/v1/activate"]
        assert "post" in activate
        assert "Activate" in activate["post"]["summary"]

    def test_register_request_schema(self, client: TestClient) -> None:
        """RegisterRequest schema has email and password fields."""
        response = client.get("/openapi.json")
        schema = response.json()
        components = schema["components"]["schemas"]
        assert "RegisterRequest" in components
        props = components["RegisterRequest"]["properties"]
        assert "email" in props
        assert "password" in props

    def test_register_response_schema(self, client: TestClient) -> None:
        """RegisterResponse schema has message and expires_in_seconds."""
        response = client.get("/openapi.json")
        schema = response.json()
        components = schema["components"]["schemas"]
        assert "RegisterResponse" in components
        props = components["RegisterResponse"]["properties"]
        assert "message" in props
        assert "expires_in_seconds" in props

    def test_activate_request_schema(self, client: TestClient) -> None:
        """ActivateRequest schema has code field."""
        response = client.get("/openapi.json")
        schema = response.json()
        components = schema["components"]["schemas"]
        assert "ActivateRequest" in components
        props = components["ActivateRequest"]["properties"]
        assert "code" in props

    def test_activate_response_schema(self, client: TestClient) -> None:
        """ActivateResponse schema has message and email fields."""
        response = client.get("/openapi.json")
        schema = response.json()
        components = schema["components"]["schemas"]
        assert "ActivateResponse" in components
        props = components["ActivateResponse"]["properties"]
        assert "message" in props
        assert "email" in props

    def test_v1_tag_in_schema(self, client: TestClient) -> None:
        """v1 tag is defined in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        tags = schema.get("tags", [])
        tag_names = [t["name"] for t in tags]
        assert "v1" in tag_names

    def test_endpoints_tagged_with_v1(self, client: TestClient) -> None:
        """Both endpoints are tagged with v1."""
        response = client.get("/openapi.json")
        schema = response.json()
        register = schema["paths"]["/v1/register"]["post"]
        activate = schema["paths"]["/v1/activate"]["post"]
        assert "v1" in register.get("tags", [])
        assert "v1" in activate.get("tags", [])


class TestSwaggerUI:
    """Tests for Swagger UI availability."""

    def test_docs_endpoint_accessible(self, client: TestClient) -> None:
        """Swagger UI is accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger" in response.text.lower()

    def test_redoc_endpoint_accessible(self, client: TestClient) -> None:
        """ReDoc is accessible at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()
