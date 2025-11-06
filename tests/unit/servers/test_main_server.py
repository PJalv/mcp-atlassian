"""Tests for the main MCP server implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_atlassian.servers.main import UserTokenMiddleware, main_mcp


@pytest.mark.anyio
async def test_run_server_stdio():
    """Test that main_mcp.run_async is called with stdio transport."""
    with patch.object(main_mcp, "run_async") as mock_run_async:
        mock_run_async.return_value = None
        await main_mcp.run_async(transport="stdio")
        mock_run_async.assert_called_once_with(transport="stdio")


@pytest.mark.anyio
async def test_run_server_sse():
    """Test that main_mcp.run_async is called with sse transport and correct port."""
    with patch.object(main_mcp, "run_async") as mock_run_async:
        mock_run_async.return_value = None
        test_port = 9000
        await main_mcp.run_async(transport="sse", port=test_port)
        mock_run_async.assert_called_once_with(transport="sse", port=test_port)


@pytest.mark.anyio
async def test_run_server_streamable_http():
    """Test that main_mcp.run_async is called with streamable-http transport and correct parameters."""
    with patch.object(main_mcp, "run_async") as mock_run_async:
        mock_run_async.return_value = None
        test_port = 9001
        test_host = "127.0.0.1"
        test_path = "/custom_mcp"
        await main_mcp.run_async(
            transport="streamable-http", port=test_port, host=test_host, path=test_path
        )
        mock_run_async.assert_called_once_with(
            transport="streamable-http", port=test_port, host=test_host, path=test_path
        )


@pytest.mark.anyio
async def test_run_server_invalid_transport():
    """Test that run_server raises ValueError for invalid transport."""
    # We don't need to patch run_async here as the error occurs before it's called
    with pytest.raises(ValueError) as excinfo:
        await main_mcp.run_async(transport="invalid")  # type: ignore

    assert "Unknown transport" in str(excinfo.value)
    assert "invalid" in str(excinfo.value)


@pytest.mark.anyio
async def test_health_check_endpoint():
    """Test the health check endpoint returns 200 and correct JSON response."""
    app = main_mcp.sse_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_sse_app_health_check_endpoint():
    """Test the /healthz endpoint on the SSE app returns 200 and correct JSON response."""
    app = main_mcp.sse_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_streamable_http_app_health_check_endpoint():
    """Test the /healthz endpoint on the Streamable HTTP app returns 200 and correct JSON response."""
    app = main_mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestUserTokenMiddleware:
    """Tests for the UserTokenMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create a UserTokenMiddleware instance for testing."""
        mock_app = AsyncMock()
        # Create a mock MCP server to avoid warnings
        mock_mcp_server = MagicMock()
        mock_mcp_server.settings.streamable_http_path = "/mcp"
        return UserTokenMiddleware(mock_app, mcp_server_ref=mock_mcp_server)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        request = MagicMock(spec=Request)
        request.url.path = "/mcp"
        request.method = "POST"
        request.headers = {}
        # Create a real state object that can be modified
        from types import SimpleNamespace

        request.state = SimpleNamespace()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        mock_response = JSONResponse({"test": "response"})
        call_next = AsyncMock(return_value=mock_response)
        return call_next

    @pytest.mark.anyio
    async def test_cloud_id_header_extraction_success(
        self, middleware, mock_request, mock_call_next
    ):
        """Test successful cloud ID header extraction."""
        # Setup request with cloud ID header
        mock_request.headers = {
            "Authorization": "Bearer test-token",
            "X-Atlassian-Cloud-Id": "test-cloud-id-123",
        }

        result = await middleware.dispatch(mock_request, mock_call_next)

        # Verify cloud ID was extracted and stored in request state
        assert hasattr(mock_request.state, "user_atlassian_cloud_id")
        assert mock_request.state.user_atlassian_cloud_id == "test-cloud-id-123"

        # Verify the request was processed normally
        mock_call_next.assert_called_once_with(mock_request)
        assert result is not None


@pytest.mark.anyio
class TestGetConnectionStatusTool:
    """Test suite for the get_connection_status tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FastMCP context."""
        from fastmcp import Context
        return MagicMock(spec=Context)

    @pytest.mark.anyio
    async def test_both_services_configured_and_working(self, mock_context):
        """Test with both services configured and working."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": True,
                "url": "https://test.atlassian.net",
                "deployment_type": "cloud",
                "authenticated_user": "user@example.com",
                "error": None,
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": True,
                "url": "https://test.atlassian.net/wiki",
                "deployment_type": "cloud",
                "authenticated_user": "user@example.com",
                "error": None,
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "healthy"
            assert "jira" in result["services"]
            assert "confluence" in result["services"]
            assert result["services"]["jira"]["authenticated"] is True
            assert result["services"]["confluence"]["authenticated"] is True
            assert "timestamp" in result

    @pytest.mark.anyio
    async def test_only_jira_configured(self, mock_context):
        """Test with only Jira configured."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": True,
                "url": "https://test.atlassian.net",
                "deployment_type": "cloud",
                "authenticated_user": "user@example.com",
                "error": None,
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": False,
                "connected": False,
                "authenticated": False,
                "url": None,
                "deployment_type": None,
                "authenticated_user": None,
                "error": "Confluence client (fetcher) not available. Ensure server is configured correctly.",
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "healthy"
            assert "jira" in result["services"]
            assert "confluence" not in result["services"]
            assert result["services"]["jira"]["authenticated"] is True

    @pytest.mark.anyio
    async def test_only_confluence_configured(self, mock_context):
        """Test with only Confluence configured."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": False,
                "connected": False,
                "authenticated": False,
                "url": None,
                "deployment_type": None,
                "authenticated_user": None,
                "error": "Jira client (fetcher) not available. Ensure server is configured correctly.",
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": True,
                "url": "https://test.atlassian.net/wiki",
                "deployment_type": "cloud",
                "authenticated_user": "user@example.com",
                "error": None,
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "healthy"
            assert "jira" not in result["services"]
            assert "confluence" in result["services"]
            assert result["services"]["confluence"]["authenticated"] is True

    @pytest.mark.anyio
    async def test_neither_service_configured(self, mock_context):
        """Test with neither service configured."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": False,
                "connected": False,
                "authenticated": False,
                "url": None,
                "deployment_type": None,
                "authenticated_user": None,
                "error": "Jira client (fetcher) not available. Ensure server is configured correctly.",
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": False,
                "connected": False,
                "authenticated": False,
                "url": None,
                "deployment_type": None,
                "authenticated_user": None,
                "error": "Confluence client (fetcher) not available. Ensure server is configured correctly.",
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "unavailable"
            assert len(result["services"]) == 0

    @pytest.mark.anyio
    async def test_authentication_failures(self, mock_context):
        """Test with authentication failures."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": False,
                "url": "https://test.atlassian.net",
                "deployment_type": "cloud",
                "authenticated_user": None,
                "error": "Unable to get current user account ID: 401 Unauthorized",
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": True,
                "connected": True,
                "authenticated": False,
                "url": "https://test.atlassian.net/wiki",
                "deployment_type": "cloud",
                "authenticated_user": None,
                "error": "Confluence token validation failed: 401 from /rest/api/user/current",
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "unavailable"
            assert "jira" in result["services"]
            assert "confluence" in result["services"]
            assert result["services"]["jira"]["authenticated"] is False
            assert result["services"]["confluence"]["authenticated"] is False
            assert "401" in result["services"]["jira"]["error"]
            assert "401" in result["services"]["confluence"]["error"]

    @pytest.mark.anyio
    async def test_network_connectivity_errors(self, mock_context):
        """Test with network/connectivity errors."""
        from mcp_atlassian.servers.main import get_connection_status_tool
        
        with patch("mcp_atlassian.servers.dependencies.check_jira_connection_status") as mock_jira, \
             patch("mcp_atlassian.servers.dependencies.check_confluence_connection_status") as mock_confluence:
            
            mock_jira.return_value = {
                "configured": True,
                "connected": False,
                "authenticated": False,
                "url": "https://test.atlassian.net",
                "deployment_type": "cloud",
                "authenticated_user": None,
                "error": "Connection timeout",
                "token_expiry": None,
            }
            mock_confluence.return_value = {
                "configured": True,
                "connected": False,
                "authenticated": False,
                "url": "https://test.atlassian.net/wiki",
                "deployment_type": "cloud",
                "authenticated_user": None,
                "error": "DNS resolution failed",
                "token_expiry": None,
            }
            
            result = await get_connection_status_tool(mock_context)
            
            assert result["overall_status"] == "unavailable"
            assert "jira" in result["services"]
            assert "confluence" in result["services"]
            assert result["services"]["jira"]["connected"] is False
            assert result["services"]["confluence"]["connected"] is False
            assert "timeout" in result["services"]["jira"]["error"]
            assert "DNS" in result["services"]["confluence"]["error"]
