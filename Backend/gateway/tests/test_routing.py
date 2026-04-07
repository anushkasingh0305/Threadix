import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response as HttpxResponse, ASGITransport

from app.main import app

# We test routing via httpx.AsyncClient against the FastAPI app directly.
# The internal _http client that proxies to upstream services is mocked.


def _mock_upstream_response(status=200, body=b'{"ok":true}'):
    """Create a fake httpx.Response that _proxy would return from upstream."""
    return HttpxResponse(
        status_code=status,
        content=body,
        headers={"content-type": "application/json"},
    )


@pytest.mark.asyncio
async def test_auth_route_login():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.post("/api/auth/auth/login", json={"email": "a@b.com", "password": "x"})
            assert resp.status_code == 200
            # Verify it proxied to the correct upstream URL
            call_kwargs = mock_http.request.call_args
            assert "auth-service:8000/auth/login" in call_kwargs.kwargs.get("url", call_kwargs[1].get("url", ""))


@pytest.mark.asyncio
async def test_auth_route_refresh():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.post("/api/auth/auth/refresh")
            assert resp.status_code == 200
            call_kwargs = mock_http.request.call_args
            url = call_kwargs.kwargs.get("url", call_kwargs[1].get("url", ""))
            assert "auth-service:8000/auth/refresh" in url


@pytest.mark.asyncio
async def test_threads_route():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.get("/api/threads/1")
            assert resp.status_code == 200
            url = mock_http.request.call_args.kwargs.get("url", mock_http.request.call_args[1].get("url", ""))
            assert "thread-service:8001/threads/1" in url


@pytest.mark.asyncio
async def test_search_route():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.get("/api/search/threads", params={"q": "hello"})
            assert resp.status_code == 200
            url = mock_http.request.call_args.kwargs.get("url", mock_http.request.call_args[1].get("url", ""))
            assert "thread-service:8001/search/threads" in url


@pytest.mark.asyncio
async def test_tags_route():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.get("/api/tags/")
            assert resp.status_code == 200
            url = mock_http.request.call_args.kwargs.get("url", mock_http.request.call_args[1].get("url", ""))
            assert "thread-service:8001/tags/" in url


@pytest.mark.asyncio
async def test_notifications_route():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.get("/api/notifications/")
            assert resp.status_code == 200
            url = mock_http.request.call_args.kwargs.get("url", mock_http.request.call_args[1].get("url", ""))
            assert "notification-service:8002/notifications/" in url


@pytest.mark.asyncio
async def test_mentions_route():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(return_value=_mock_upstream_response())
            resp = await client.get("/api/mentions", params={"q": "ali"})
            assert resp.status_code == 200
            url = mock_http.request.call_args.kwargs.get("url", mock_http.request.call_args[1].get("url", ""))
            assert "thread-service:8001/search/users" in url


@pytest.mark.asyncio
async def test_unknown_route_returns_404():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            resp = await client.get("/api/unknown/path")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Route not found"
            mock_http.request.assert_not_called()


@pytest.mark.asyncio
async def test_upstream_down_returns_503():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.main._http") as mock_http:
            mock_http.request = AsyncMock(side_effect=httpx.RequestError("connection refused"))
            resp = await client.get("/api/threads/1")
            assert resp.status_code == 503
            assert "unavailable" in resp.json()["detail"].lower()
