import asyncio
import httpx
import websockets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from websockets.exceptions import ConnectionClosed

UPSTREAM = {
    "auth":          "http://auth-service:8000",
    "thread":        "http://thread-service:8001",
    "notification":  "http://notification-service:8002",
}

HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]

_STRIP_REQ  = {"host", "content-length", "transfer-encoding"}
_STRIP_RESP = {"content-encoding", "transfer-encoding", "content-length"}

_http: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=30.0)
    yield
    await _http.aclose()


app = FastAPI(title="Threadix API Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── HTTP proxy helper ────────────────────────────────────────────────────────

async def _proxy(request: Request, target_url: str) -> Response:
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in _STRIP_REQ}
    body = await request.body()
    try:
        resp = await _http.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
            follow_redirects=False,
        )
    except httpx.RequestError:
        return Response(
            content=b'{"detail":"Service temporarily unavailable"}',
            status_code=503,
            media_type="application/json",
        )

    resp_headers = {k: v for k, v in resp.headers.items()
                    if k.lower() not in _STRIP_RESP}
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
    )


# ─── HTTP routing ─────────────────────────────────────────────────────────────
# Single catch-all: /api/{rest:path} — first segment determines the service.

@app.api_route("/api/{rest:path}", methods=HTTP_METHODS)
async def gateway_http(request: Request, rest: str):
    parts   = rest.split("/", 1)
    service = parts[0]
    sub     = parts[1] if len(parts) > 1 else ""

    if service == "auth":
        # /api/auth/auth/login → auth-service:8000/auth/login
        return await _proxy(request, f"{UPSTREAM['auth']}/{sub}")

    if service in ("threads", "search", "tags"):
        # /api/threads/1 → thread-service:8001/threads/1
        return await _proxy(request, f"{UPSTREAM['thread']}/{service}/{sub}")

    if service == "notifications":
        # /api/notifications/ → notification-service:8002/notifications/
        return await _proxy(request, f"{UPSTREAM['notification']}/notifications/{sub}")

    if service == "mentions":
        # /api/mentions?q=prefix → thread-service:8001/search/users?q=prefix
        return await _proxy(request, f"{UPSTREAM['thread']}/search/users")

    return Response(
        content=b'{"detail":"Route not found"}',
        status_code=404,
        media_type="application/json",
    )


# ─── WebSocket proxy helper ───────────────────────────────────────────────────

async def _ws_proxy(ws_client: WebSocket, backend_url: str):
    # Forward query string (e.g. ?channels=...) to upstream
    query_string = ws_client.scope.get("query_string", b"").decode()
    if query_string:
        backend_url += f"?{query_string}"

    cookie = ws_client.headers.get("cookie", "")
    extra  = {"cookie": cookie} if cookie else {}

    await ws_client.accept()
    try:
        async with websockets.connect(backend_url, additional_headers=extra) as ws_back:

            async def c2b():
                try:
                    while True:
                        data = await ws_client.receive_text()
                        await ws_back.send(data)
                except (WebSocketDisconnect, Exception):
                    pass

            async def b2c():
                try:
                    async for msg in ws_back:
                        await ws_client.send_text(str(msg))
                except (ConnectionClosed, Exception):
                    pass

            done, pending = await asyncio.wait(
                [asyncio.create_task(c2b()), asyncio.create_task(b2c())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

    except Exception:
        try:
            await ws_client.close(code=1011)
        except Exception:
            pass


# ─── WebSocket routing ────────────────────────────────────────────────────────
# More-specific route MUST be defined before the catch-all.

@app.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    await _ws_proxy(ws, f"ws://notification-service:8002/ws/notifications")


@app.websocket("/ws")
async def ws_thread_base(ws: WebSocket):
    """Handle /ws?channels=... (no sub-path) — most common client connection."""
    await _ws_proxy(ws, "ws://thread-service:8001/ws")


@app.websocket("/ws/{path:path}")
async def ws_thread(ws: WebSocket, path: str):
    base = f"ws://thread-service:8001/ws/{path}" if path else "ws://thread-service:8001/ws"
    await _ws_proxy(ws, base)


# ─── Gateway health ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "gateway ok"}
