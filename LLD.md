# Threadix — Low-Level Design (LLD)

Every file in the project is explained line by line or block by block below.

---

## PART 1 — GATEWAY SERVICE

### `Backend/gateway/app/main.py`

```python
import asyncio
```
Imports Python's built-in `asyncio` library. Used for `asyncio.wait()` and `asyncio.create_task()` inside the WebSocket proxy to run two coroutines (client→backend, backend→client) concurrently.

```python
import httpx
```
Imports `httpx`, an async-capable HTTP client. The gateway uses this to forward all browser HTTP requests to the appropriate backend service. Unlike `requests`, `httpx` supports `async/await`.

```python
import websockets
```
Imports the `websockets` library (not FastAPI's built-in WS support). Used specifically for the **gateway-to-backend** WebSocket connection. The gateway receives a WS on the FastAPI side and opens a new WS to the backend using this library.

```python
from contextlib import asynccontextmanager
```
Imports the decorator used to write a `lifespan` async generator. This controls what happens at app startup (before `yield`) and shutdown (after `yield`).

```python
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
```
`FastAPI` — the framework class.
`Request` — represents the incoming HTTP request (headers, body, query params, cookies).
`Response` — the outgoing HTTP response object.
`WebSocket` — represents an incoming WebSocket connection from the browser.
`WebSocketDisconnect` — exception raised when the browser closes the WebSocket.

```python
from fastapi.middleware.cors import CORSMiddleware
```
Imports the CORS middleware. CORS (Cross-Origin Resource Sharing) is required because the frontend (port 5173) calls the API (port 8080) — different origins.

```python
from websockets.exceptions import ConnectionClosed
```
Exception raised by the `websockets` library when the backend WebSocket closes. Caught in the proxy tasks to cleanly stop forwarding.

```python
UPSTREAM = {
    "auth":         "http://auth-service:8000",
    "thread":       "http://thread-service:8001",
    "notification": "http://notification-service:8002",
}
```
A dictionary mapping URL path prefixes to backend service base URLs. Services are reachable by container name inside the `threadix` Docker bridge network. When the gateway receives `/api/auth/...`, it looks up `UPSTREAM["auth"]` to get the target URL.

```python
HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
```
The list of HTTP methods that the catch-all route should accept. Passed to `@app.api_route(methods=...)`. `OPTIONS` is needed for CORS preflight requests sent by the browser before cross-origin POST/PUT calls.

```python
_STRIP_REQ  = {"host", "content-length", "transfer-encoding"}
```
Set of request headers to remove before forwarding to the backend. Removing `host` prevents the upstream from receiving the browser's original `Host: localhost:8080` (it should see its own host). Removing `content-length` and `transfer-encoding` avoids conflicts when httpx recalculates them for the forwarded body.

```python
_STRIP_RESP = {"content-encoding", "transfer-encoding", "content-length"}
```
Set of response headers to remove before sending back to the browser. Removing `content-encoding` prevents double-decompression if httpx already decoded gzip. Removing `content-length` avoids length mismatches since the gateway re-streams the body.

```python
_http: httpx.AsyncClient = None
```
Module-level variable to hold the shared httpx client. Initialized as `None`; created in `lifespan`. Using one shared client (instead of creating per-request) reuses the underlying TCP connection pool, which is much faster under load.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http
    _http = httpx.AsyncClient(timeout=30.0)
    yield
    await _http.aclose()
```
`@asynccontextmanager` + `async def lifespan(app)` — this is FastAPI's startup/shutdown hook pattern.
Before `yield`: creates one shared `httpx.AsyncClient` with a 30-second default timeout. Setting `timeout=30.0` means any backend call that takes more than 30 seconds will raise an error rather than blocking forever.
After `yield`: `_http.aclose()` gracefully closes all open connections in the pool when the server shuts down.

```python
app = FastAPI(title="Threadix API Gateway", lifespan=lifespan)
```
Creates the FastAPI application. `title` sets the OpenAPI docs title. `lifespan=lifespan` wires up the startup/shutdown logic defined above.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Adds CORS middleware. `allow_credentials=True` is essential — it tells the browser it may send cookies with cross-origin requests (needed for httpOnly JWT cookies). `allow_origins` is an explicit whitelist — not `"*"` — because `allow_credentials=True` and `"*"` origin are incompatible in browsers. `allow_methods=["*"]` and `allow_headers=["*"]` permit any method/header.

```python
async def _proxy(request: Request, target_url: str) -> Response:
```
The core HTTP forwarding function. Takes the original browser request and the fully constructed target URL (e.g., `http://thread-service:8001/threads/1`) and returns a FastAPI `Response`.

```python
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in _STRIP_REQ}
```
Build a new headers dict from the incoming request, excluding the headers in `_STRIP_REQ`. `k.lower()` normalizes header names since HTTP headers are case-insensitive.

```python
    body = await request.body()
```
Reads the entire request body as bytes. `await` is required because the body is read asynchronously from the socket. For GET requests this is empty bytes.

```python
    try:
        resp = await _http.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
            follow_redirects=False,
        )
```
Forwards the request to the backend using the shared httpx client. `method` is passed through unchanged (GET, POST, etc.). `content=body` sends the raw bytes. `params=dict(request.query_params)` forwards query string parameters (e.g., `?limit=20`). `follow_redirects=False` — the gateway should not automatically follow 3xx redirects from backends; return them to the client.

```python
    except httpx.RequestError:
        return Response(
            content=b'{"detail":"Service temporarily unavailable"}',
            status_code=503,
            media_type="application/json",
        )
```
If the backend is unreachable (connection refused, DNS failure, timeout) `httpx.RequestError` is raised. Return 503 Service Unavailable to the browser instead of crashing.

```python
    resp_headers = {k: v for k, v in resp.headers.items()
                    if k.lower() not in _STRIP_RESP}
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
    )
```
Build the response to return to the browser. Strip problematic response headers. `resp.content` is the full response body bytes. `resp.status_code` preserves the backend's status (200, 201, 400, etc.).

```python
@app.api_route("/api/{rest:path}", methods=HTTP_METHODS)
async def gateway_http(request: Request, rest: str):
```
`@app.api_route` registers a route for multiple HTTP methods at once. `{rest:path}` is a path parameter that matches the rest of the URL **including slashes** (e.g., `auth/auth/login` or `threads/5/comments/`). `rest` is passed as a function parameter.

```python
    parts   = rest.split("/", 1)
    service = parts[0]
    sub     = parts[1] if len(parts) > 1 else ""
```
Splits the path at the first `/`. `service` = first segment (e.g., `"auth"`, `"threads"`, `"notifications"`). `sub` = remainder (e.g., `"auth/login"` or `"5/comments/"`). The `1` in `split("/", 1)` limits to one split — prevents over-splitting.

```python
    if service == "auth":
        return await _proxy(request, f"{UPSTREAM['auth']}/{sub}")
```
`/api/auth/auth/login` → `service="auth"`, `sub="auth/login"` → forwards to `http://auth-service:8000/auth/login`.

```python
    if service in ("threads", "search", "tags"):
        return await _proxy(request, f"{UPSTREAM['thread']}/{service}/{sub}")
```
`/api/threads/5` → `service="threads"`, `sub="5"` → `http://thread-service:8001/threads/5`.
The `service` prefix is kept in the path because the thread service routes are prefixed with `/threads`, `/search`, `/tags`.

```python
    if service == "notifications":
        return await _proxy(request, f"{UPSTREAM['notification']}/notifications/{sub}")
```
`/api/notifications/unread-count` → forwards to `http://notification-service:8002/notifications/unread-count`.

```python
    if service == "mentions":
        return await _proxy(request, f"{UPSTREAM['thread']}/search/users")
```
`/api/mentions?q=ali` → maps to thread service's user autocomplete endpoint. The query string is forwarded automatically by `params=dict(request.query_params)` in `_proxy`.

```python
    return Response(
        content=b'{"detail":"Route not found"}',
        status_code=404,
        media_type="application/json",
    )
```
If nothing matched, return a 404 JSON response. This is the gateway's own 404 — distinct from a backend's 404.

```python
async def _ws_proxy(ws_client: WebSocket, backend_url: str):
```
The WebSocket bidirectional proxy. `ws_client` is the browser's incoming WS connection (FastAPI `WebSocket`). `backend_url` is the target backend WebSocket URL.

```python
    query_string = ws_client.scope.get("query_string", b"").decode()
    if query_string:
        backend_url += f"?{query_string}"
```
Reads the raw query string from ASGI scope. If the browser connected as `/ws?channels=thread:1:comments`, `query_string = "channels=thread:1:comments"` is appended to the backend URL so the backend receives the same params.

```python
    cookie = ws_client.headers.get("cookie", "")
    extra  = {"cookie": cookie} if cookie else {}
```
Extracts the `Cookie` header from the browser's WS request. This is how the JWT access_token cookie is forwarded to the backend service for authentication. `extra` is passed to `websockets.connect(additional_headers=...)`.

```python
    await ws_client.accept()
```
Accepts the browser's WebSocket upgrade. The TCP handshake + HTTP 101 Switching Protocols response happens here. Must be called before sending/receiving any WS data.

```python
    async with websockets.connect(backend_url, additional_headers=extra) as ws_back:
```
Opens a new WebSocket connection from the gateway TO the backend service. `additional_headers=extra` forwards the cookie. The `async with` block ensures the backend connection is closed when the block exits.

```python
        async def c2b():  # client → backend
            try:
                while True:
                    data = await ws_client.receive_text()
                    await ws_back.send(data)
            except (WebSocketDisconnect, Exception):
                pass
```
Coroutine that reads messages from the browser and forwards them to the backend. The `except` silently exits when either side closes.

```python
        async def b2c():  # backend → client
            try:
                async for msg in ws_back:
                    await ws_client.send_text(str(msg))
            except (ConnectionClosed, Exception):
                pass
```
Coroutine that reads messages from the backend and forwards them to the browser. `async for msg in ws_back` automatically handles the backend's pub/sub stream.

```python
        done, pending = await asyncio.wait(
            [asyncio.create_task(c2b()), asyncio.create_task(b2c())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
```
Runs both coroutines concurrently. `asyncio.wait(..., return_when=FIRST_COMPLETED)` returns as soon as **either** direction closes (browser disconnect or backend disconnect). The remaining running task is cancelled — no orphaned goroutines.

```python
    except Exception:
        try:
            await ws_client.close(code=1011)
        except Exception:
            pass
```
If something fails during the WS setup (e.g., backend is down), attempt to close the browser connection with code 1011 (Unexpected condition). The nested try/except ignores errors if the browser already closed.

```python
@app.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    await _ws_proxy(ws, f"ws://notification-service:8002/ws/notifications")
```
Most-specific `/ws/notifications` route. **Must be defined before** the catch-all `/ws/{path:path}` route because FastAPI matches routes in definition order. Forwards directly to the notification service.

```python
@app.websocket("/ws")
async def ws_thread_base(ws: WebSocket):
    await _ws_proxy(ws, "ws://thread-service:8001/ws")
```
Handles `/ws` with no sub-path (bare connection with `?channels=...` query string). The most common client connection pattern from FeedPage and ThreadDetailPage.

```python
@app.websocket("/ws/{path:path}")
async def ws_thread(ws: WebSocket, path: str):
    base = f"ws://thread-service:8001/ws/{path}" if path else "ws://thread-service:8001/ws"
    await _ws_proxy(ws, base)
```
Catch-all for any sub-path under `/ws/` (except `/ws/notifications` which is handled above). Forwards to the thread service with the sub-path appended.

```python
@app.get("/health")
async def health():
    return {"status": "gateway ok"}
```
Simple health check endpoint. Used by Docker `HEALTHCHECK` directive and load balancers to verify the gateway is alive.

---

## PART 2 — AUTH SERVICE

### `Backend/services/auth-service/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.utils.logger import logger
from app.api.routes import auth, user
import app.core.cloudinary_config  # noqa: F401
```
Standard imports. `import app.core.cloudinary_config` with `# noqa: F401` is a bare import with no name — it's imported purely for its **side effect** of calling `cloudinary.config(...)` on startup. The `noqa` comment tells linters to ignore the "imported but unused" warning.

```python
app = FastAPI(title="Threadix Auth Service")
```
Creates the FastAPI app. No `lifespan` here — auth-service relies on Alembic migrations (run at container startup via `CMD`) rather than `create_all` inside Python.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
CORS configuration. Allows cookies to be sent. In production traffic, the gateway handles CORS so this middleware acts as a safety net for direct debug access.

```python
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])
```
Registers two routers. All auth endpoints are under `/auth/...`, all user endpoints under `/user/...`. `tags` groups them in the auto-generated OpenAPI docs.

```python
@app.on_event("startup")
async def startup():
    logger.info("Auth Service Started")
```
Legacy-style startup event. Just logs a message when the service is ready. (Modern FastAPI uses `lifespan`; this older pattern still works.)

---

### `Backend/services/auth-service/app/core/config.py`

The Pydantic `Settings` class reads all configuration from environment variables (or a `.env` file). Key fields:

- `DATABASE_URL` — SQLAlchemy async connection string for PostgreSQL
- `SECRET_KEY` — shared HS256 signing key for JWTs (same value used in all services)
- `ALGORITHM` — `"HS256"` (HMAC-SHA256)
- `REDIS_URL` — `redis://:password@redis:6379/0`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` — for avatar upload

Pydantic Settings automatically validates types and raises an error at startup if required values are missing.

---

### `Backend/services/auth-service/app/core/security.py`

```python
from datetime import datetime, timedelta
import jwt
from app.core.config import settings
```
Imports: `datetime` + `timedelta` for expiry calculation, `jwt` (PyJWT library), `settings` for SECRET_KEY and ALGORITHM.

```python
def create_access_token(data: dict):
    to_encode = data.copy()
```
Takes a copy of `data` to avoid mutating the caller's dict.

```python
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
```
Access tokens expire in 15 minutes. `"exp"` is the standard JWT expiry claim — PyJWT enforces it automatically during `decode`.

```python
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```
Signs and encodes the payload as a compact JWT string (`header.payload.signature`). The signature uses HMAC-SHA256 with `SECRET_KEY`.

```python
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```
Same as access token but 7-day expiry and the payload only contains `"sub"` (user ID). Refresh tokens are intentionally minimal — they're stored as a hash in Redis and can be invalidated.

```python
def decode_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```
Decodes and **verifies** a JWT token. This raises `jwt.ExpiredSignatureError` if expired and `jwt.InvalidTokenError` if tampered with or signed with a different key. `algorithms` is a list — prevents algorithm-confusion attacks (e.g., RS256 vs HS256).

---

### `Backend/services/auth-service/app/core/hashing.py`

```python
import bcrypt

def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```
`bcrypt.gensalt()` generates a random salt (default 12 rounds). `hashpw` computes the salted bcrypt hash. `.encode()` converts the string to bytes (bcrypt requires bytes). `.decode()` converts the resulting bytes back to a string for database storage.

```python
def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode(), hashed.encode())
```
`bcrypt.checkpw` is constant-time — prevents timing attacks. It extracts the salt from `hashed` and re-hashes `password` to compare. Returns `True` if they match.

---

### `Backend/services/auth-service/app/core/dependencies.py`

```python
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
```
Reads the `access_token` cookie from the request. If absent, rejects with 401.

```python
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id
```
Decodes the JWT and returns `user_id` (the `"sub"` claim) as a string. Auth-service routes only need the user_id, not the full payload.

```python
def require_role(required_roles: list):
    async def role_checker(request: Request):
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        payload = decode_token(token)
        role = payload.get("role")
        if role not in required_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return payload.get("sub")
    return role_checker
```
A **factory function** that returns a FastAPI dependency. `required_roles` is captured via closure. When used as `Depends(require_role(["admin"]))`, FastAPI calls `role_checker` for each request and passes the JWT's role through the whitelist check.

---

### `Backend/services/auth-service/app/db/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
```
Creates the async SQLAlchemy engine. `echo=True` logs every SQL statement — useful for development debugging.

```python
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```
A session factory. `expire_on_commit=False` means ORM objects remain usable after `commit()` without requiring another database round-trip to reload them. Critical for returning data from service functions after committing.

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```
FastAPI dependency that provides a database session. `async with` auto-closes the session (and rolls back on uncaught exceptions). `yield` makes it a generator-based dependency — the session lives until the request completes.

---

### `Backend/services/auth-service/app/db/redis.py`

```python
from redis.asyncio import from_url
from app.core.config import settings

redis = from_url(settings.REDIS_URL, decode_responses=True)
```
Creates a Redis connection at module level. `decode_responses=True` automatically decodes Redis byte responses to Python strings (saves calling `.decode()` everywhere). `from_url` parses `redis://:password@host:port/db_number`.

```python
async def set_key(key: str, value: str, expire: int | None = None):
    await redis.set(key, value, ex=expire)
```
`ex=expire` sets the TTL in seconds. `ex=None` creates a key with no expiry. Used for storing the refresh token hash: `set_key(f"refresh:{user_id}", sha256_hash, expire=7*24*60*60)`.

```python
async def get_key(key: str) -> str | None:
    return await redis.get(key)
```
Returns `None` if the key doesn't exist or has expired.

```python
async def delete_key(key: str):
    await redis.delete(key)
```
Deletes a key immediately. Used on logout and on token rotation (old token invalidated).

---

### `Backend/services/auth-service/app/db/models.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()
```
`declarative_base()` creates the base class for all ORM models. All models inherit from `Base` so SQLAlchemy knows they belong to the same schema. Only one `Base` per database.

```python
class UserRole(str, enum.Enum):
    admin = "admin"
    moderator = "moderator"
    member = "member"
```
Inheriting from both `str` and `enum.Enum` means instances compare equal to their string values: `UserRole.admin == "admin"` is `True`. This is important for JSON serialization (Pydantic can serialize it as a string).

```python
class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    username   = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role       = Column(Enum(UserRole), default=UserRole.member)
    bio        = Column(String(300), nullable=True)
    avatar_url = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```
`index=True` on `email` and `username` creates DB indexes for fast lookup.
`unique=True` enforces no duplicate emails/usernames at the database level (not just application).
`default=UserRole.member` means new users are always `member` unless explicitly set.
`onupdate=datetime.utcnow` automatically updates `updated_at` when the record is changed.
`is_deleted=False` is a soft-delete flag — we never `DELETE` rows from the table.

---

### `Backend/services/auth-service/app/db/schemas.py`

```python
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=3, max_length=20)
```
`EmailStr` (from Pydantic) validates that the email is syntactically valid. `Field(min_length=6)` rejects passwords shorter than 6 characters at the Pydantic validation level — before even touching the database.

```python
class UpdateProfile(BaseModel):
    username: str | None = None
    bio: str | None = Field(None, max_length=300)
```
All fields optional (can update partial profile). `str | None = None` uses Python 3.10+ union syntax — equivalent to `Optional[str] = None`.

```python
class UserProfile(BaseModel):
    ...
    class Config:
        from_attributes = True
```
`from_attributes = True` (formerly `orm_mode = True`) tells Pydantic to read data from ORM object attributes (SQLAlchemy model instances) instead of only from dicts. Required to use `UserProfile.model_validate(user_orm_object)`.

---

### `Backend/services/auth-service/app/repositories/user_repository.py`

```python
class UserRepository:
    @staticmethod
    async def get_by_email(db, email):
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
```
Uses SQLAlchemy's `select()` to build a SELECT query. `scalar_one_or_none()` returns the first result as a Python object or `None` — it raises an error if more than one row is returned (impossible here due to `unique=True` on email).

```python
    @staticmethod
    async def create_user(db, user):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
```
`db.add(user)` marks the ORM object for INSERT. `await db.commit()` executes the INSERT and commits the transaction. `await db.refresh(user)` re-reads the object from DB to populate auto-generated fields like `id` and `created_at`.

---

### `Backend/services/auth-service/app/services/auth_service.py`

```python
import hashlib
ALLOWED_ROLES = {"admin", "moderator", "member"}
```
`hashlib` is used for SHA-256 hashing of refresh tokens. `ALLOWED_ROLES` is a guard against future database corruption where an invalid role value might exist.

```python
async def register_user(db, user_data):
    if await UserRepository.get_by_email(db, user_data.email):
        raise Exception("Email already exists")
    if await UserRepository.get_by_username(db, user_data.username):
        raise Exception("Username already taken")
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role=UserRole.member
    )
    return await UserRepository.create_user(db, user)
```
Two uniqueness checks before INSERT — duplicate email and username. `hash_password` runs bcrypt (blocking operation in async context — acceptable for low-frequency operations like registration). `role=UserRole.member` hardcodes the initial role regardless of what the client might send.

```python
async def login_user(db, user_data):
    user = await UserRepository.get_by_email(db, user_data.email)
    if not user or user.is_deleted:
        raise Exception("User not found")
    if not verify_password(user_data.password, user.password_hash):
        raise Exception("Invalid password")
    if user.role.value not in ALLOWED_ROLES:
        raise Exception("Invalid role")
```
Intentionally uses the same vague error messages for "not found" and "deleted" — prevents user enumeration via different error messages.

```python
    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "email": user.email,
    })
    refresh_token = create_refresh_token({"sub": str(user.id)})
    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    await set_key(f"refresh:{user.id}", hashed, expire=7*24*60*60)
    return access_token, refresh_token
```
The access token contains the full user profile — downstream services can verify and use identity without calling auth-service. The refresh token only needs the `sub` (user ID). The actual refresh token is **never stored in Redis** — only its SHA-256 hash. This means even if Redis is compromised, the attacker cannot use the hash to forge a token.

```python
async def refresh_tokens(refresh_token: str, db=None):
    payload = decode_token(refresh_token)
    user_id = payload.get("sub")
    stored = await get_key(f"refresh:{user_id}")
    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    if not stored or stored != hashed:
        raise Exception("Session expired or token reuse")
    await delete_key(f"refresh:{user_id}")
```
Token rotation:
1. Decode to get user_id
2. Look up stored SHA-256 hash in Redis
3. Compute SHA-256 of the submitted token and compare
4. If they don't match → someone already used this token (or it was stolen) → reject
5. Delete the old hash immediately (one-time-use)

```python
    if db is not None:
        user = await UserRepository.get_by_id(db, int(user_id))
        if user:
            access_payload["role"] = user.role.value
            ...
```
On refresh, the new access token is built from **fresh database data** — not from the old token's claims. This means role changes take effect at the next refresh rather than waiting for a new login.

---

### `Backend/services/auth-service/app/api/routes/auth.py`

```python
@router.post("/login")
async def login(user: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        access, refresh = await login_user(db, user)
        response.set_cookie("access_token", access, httponly=True)
        response.set_cookie("refresh_token", refresh, httponly=True)
        return {"message": "Login successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```
`response: Response` — FastAPI injects the response object so we can set cookies on it. `httponly=True` — the cookie cannot be read by JavaScript. This protects the tokens from XSS attacks.

```python
@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")
    ...
    try:
        payload = decode_token(token)
        await logout_user(payload["sub"])
    except Exception:
        pass  # still clear cookies even if token is expired
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
```
The `except: pass` block is intentional. If the access token is already expired, we still want to clear cookies and delete the Redis refresh token hash. The try/except prevents a 500 error when logging out with an expired token.

---

### `Backend/services/auth-service/app/services/user_service.py`

```python
async def update_user_profile(db, user_id, data, file=None):
    ...
    if data.username:
        result = await db.execute(
            select(User).where(User.username == data.username)
        )
        existing = result.scalar_one_or_none()
        if existing and existing.id != int(user_id):
            raise Exception("Username already taken")
        user.username = data.username
```
When changing a username, check if it's already taken **by a different user**. `existing.id != int(user_id)` allows a user to "update" their profile with the same username they already have (idempotent update).

```python
    if file:
        if not file.content_type.startswith("image/"):
            raise Exception("Only image files allowed")
        try:
            upload = cloudinary.uploader.upload(file.file)
            user.avatar_url = upload["secure_url"]
        except Exception:
            raise Exception("Avatar upload failed")
```
MIME type validation before upload. `file.content_type` is the MIME type from the `Content-Type` header. `cloudinary.uploader.upload(file.file)` passes the file object directly to the Cloudinary SDK. `upload["secure_url"]` is the HTTPS CDN URL of the uploaded image.

---

### `Backend/services/auth-service/app/api/routes/user.py`

```python
@router.get("/list")
async def list_users(limit: int = 50, offset: int = 0, ...):
    total = await db.scalar(
        select(func.count()).select_from(User).where(User.is_deleted == False)
    )
    result = await db.execute(
        select(User).where(User.is_deleted == False)
        .order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
```
`func.count()` calls `COUNT(*)` in SQL. `select_from(User)` tells SQLAlchemy which table to count. Two separate queries: one for total count (for pagination metadata), one for the actual page of results.

```python
@router.put("/role/{username}")
async def set_user_role(username: str, role: UserRole, ...):
    user = await UserRepository.get_by_username(db, username)
    user.role = role
```
`UserRole` is the enum type — FastAPI validates the submitted value automatically. If the string is not `"admin"`, `"moderator"`, or `"member"`, a 422 Unprocessable Entity is returned.

---

## PART 3 — THREAD SERVICE

### `Backend/services/thread-service/app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_cloudinary()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```
`engine.begin()` opens a connection and starts a transaction. `run_sync(Base.metadata.create_all)` runs the synchronous `create_all` inside the async engine context — required because SQLAlchemy's `create_all` is sync-only. This creates all 8 tables if they don't exist. For thread service, there are no Alembic migrations — schema is managed via `create_all`.

```python
    async for db in get_db():
        await TagRepository.seed(db)
        break
```
Gets one database session and runs `seed()` to insert the default tags if they don't already exist. `break` exits after the first iteration — only one seeding run needed at startup.

---

### `Backend/services/thread-service/app/core/dependencies.py`

```python
@dataclass
class CurrentUser:
    id: int
    username: str
    avatar_url: Optional[str]
    role: str
```
A lightweight data class to carry the decoded user identity through request handlers. Using a dataclass instead of a raw dict ensures type safety and attribute access (`.id`, `.role`).

```python
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
```
`Cookie(default=None)` — FastAPI extracts the `access_token` cookie automatically. Returns `None` if the cookie is absent (for optional auth routes that call this).

```python
    await UserCacheRepository.upsert(db, user_id, username, avatar, role)
```
Every authenticated request silently updates `users_cache` with the latest JWT claims. This is the **passive synchronization mechanism** — if an admin changes a user's role, the next time that user makes a request, their new role is reflected in the thread service's users_cache.

```python
def rate_limit(key_prefix: str, limit: int, window_seconds: int = 60):
    async def _check(current_user: CurrentUser = Depends(get_current_user)):
        key = f'rl:{key_prefix}:{current_user.id}'
        count = await increment_rate_limit(key, window_seconds)
        if count > limit:
            raise RateLimitError()
        return current_user
    return _check
```
Factory function that creates a per-user, per-operation rate limit dependency. `increment_rate_limit` uses Redis `INCR` + `EXPIRE` pipeline. On first call in the window, INCR sets count=1 and EXPIRE sets the TTL. Subsequent calls increment the counter; once `count > limit`, requests are rejected with 429.

---

### `Backend/services/thread-service/app/api/routes/threads.py`

```python
@router.post('/', dependencies=[Depends(rate_limit('thread_create', 5))])
async def create(
    title: str = Form(...),
    description: str = Form(...),
    tag_ids: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    ...
```
`dependencies=[Depends(...)]` applies rate limiting without adding it as a function parameter. `Form(...)` reads values from `multipart/form-data` fields. The thread creation endpoint accepts multipart (not JSON) because it supports file uploads — JSON bodies cannot carry binary file data.

```python
    parsed_tag_ids = [int(i) for i in tag_ids.split(',') if i] if tag_ids else []
```
`tag_ids` arrives as a comma-separated string (e.g., `"1,3,7"` from the form). List comprehension splits and converts each ID; the `if i` guard skips empty strings from trailing commas.

```python
@router.get('/{thread_id}')
async def get_one(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[CurrentUser] = Depends(get_current_user),
):
    thread, user_has_liked = await get_thread(db, thread_id, user)
    return {**thread.__dict__, 'user_has_liked': user_has_liked}
```
`Optional[CurrentUser]` — auth is optional here. Anonymous users can view threads. `thread.__dict__` spreads all ORM attributes into the dict; `'user_has_liked'` is added to tell the frontend whether to show the like button as active.

---

### `Backend/services/thread-service/app/api/routes/comments.py`

```python
@router.get('/')
async def get_top_level_comments(thread_id: int, ...):
    comments, total = await CommentRepository.get_top_level(db, thread_id, limit, offset)
    result = []
    for c in comments:
        child_count = await CommentRepository.count_children(db, c.id)
        result.append({**c.__dict__, 'child_count': child_count})
```
For each top-level comment, a separate query counts its children. This is N+1 queries but acceptable at page sizes of 20 — the `child_count` enables the "Load N replies" button in the frontend without loading the actual children yet.

```python
@router.get('/{comment_id}/children')
async def load_more_children(thread_id: int, comment_id: int, ...):
    children, total = await CommentRepository.get_children(db, comment_id, limit, offset)
```
Lazy loading of nested replies. Called only when the user clicks "Load more replies", avoiding loading the entire comment tree upfront.

---

### `Backend/services/thread-service/app/api/routes/websocket.py`

```python
@router.websocket('/ws')
async def websocket_endpoint(ws: WebSocket, channels: str = Query(...)):
    await ws.accept()
    channel_list = [c.strip() for c in channels.split(',') if c.strip()]
```
`Query(...)` reads `?channels=` from the WebSocket upgrade URL query string. The `...` means it's required. `c.strip()` removes whitespace; `if c.strip()` skips empty strings from double commas.

```python
    pubsub_objects = []
    for channel in channel_list:
        ps = await subscribe_to_channel(channel)
        pubsub_objects.append(ps)
```
Creates one Redis pub/sub subscription per requested channel. Each `ps` is an independent Redis pub/sub object with its own message queue.

```python
    tasks = [
        asyncio.create_task(_forward_messages(ws, ps))
        for ps in pubsub_objects
    ]
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        for task in tasks:
            task.cancel()
        for ps in pubsub_objects:
            await ps.unsubscribe()
```
`_forward_messages` runs concurrently for each subscribed channel. The `while True: receive_text()` block keeps the connection alive and detects client disconnect. On disconnect, all forwarding tasks are cancelled and Redis subscriptions are cleaned up.

---

### `Backend/services/thread-service/app/db/redis.py`

```python
_redis: aioredis.Redis = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
```
Lazy singleton pattern for the Redis connection. On first call, creates the connection; subsequent calls return the cached connection. Avoids creating multiple connection pools.

```python
async def publish_event(channel: str, payload: dict):
    r = await get_redis()
    await r.publish(channel, json.dumps(payload))
```
Serializes the payload dict to JSON string and publishes to the Redis channel. All subscribers to that channel receive the JSON string as a message.

```python
async def increment_rate_limit(key: str, window_seconds: int) -> int:
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    return results[0]
```
Uses a Redis pipeline to batch `INCR` and `EXPIRE` as a single round-trip. `pipe.expire(key, window_seconds)` only sets the TTL if the key doesn't already have one (Redis behavior: EXPIRE on an existing TTL-less key sets it; on a key with TTL it resets it — which is the desired sliding window behavior).

---

### `Backend/services/thread-service/app/services/comment_service.py`

```python
MENTION_RE = re.compile(r'@([a-zA-Z0-9_]+)')
```
Compiled regex to extract @mentions from comment content. `([a-zA-Z0-9_]+)` captures only alphanumeric + underscore characters after `@` (valid username characters).

```python
async def _update_affinity(db, user_id, thread_id, weight):
    stmt = insert(UserTagAffinity).values(
        user_id=user_id, tag_id=tag_id, score=weight
    ).on_conflict_do_update(
        index_elements=['user_id', 'tag_id'],
        set_={'score': UserTagAffinity.score + weight}
    )
```
PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` — atomic upsert. If the `(user_id, tag_id)` combination already exists, add `weight` to the existing score. If it doesn't, create it with `score=weight`. This is entirely atomic at the database level.

```python
async def create_comment(db, user, thread_id, data):
    ...
    depth = 0
    if data.parent_id:
        parent = await CommentRepository.get_by_id(db, data.parent_id)
        if parent.thread_id != thread_id:
            raise ValidationError('Parent comment does not belong to this thread')
        depth = parent.depth + 1
        if depth > MAX_COMMENT_DEPTH:
            raise ValidationError(f'Max comment depth is {MAX_COMMENT_DEPTH}')
```
Threaded comment validation: cross-thread parent injection is blocked. Depth enforcement prevents infinitely nested trees. `MAX_COMMENT_DEPTH = 4` means you can have 5 levels (0–4).

```python
    mentioned_usernames = set(MENTION_RE.findall(data.content))
    for username in mentioned_usernames:
        ...
        exact = [u for u in mentioned_user_results if u.username == username]
        if exact:
            await publish_event(f'user:{exact[0].id}:notifs', {...})
```
`set(...)` deduplicates mentions (mentioning `@alice @alice` only triggers one notification). Only exact username matches trigger notifications — prefix matches are for autocomplete only.

---

## PART 4 — NOTIFICATION SERVICE

### `Backend/services/notification-service/app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    consumer_task = asyncio.create_task(start_consumer())
    logger.info('Notification service started. Consumer running.')
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
```
`asyncio.create_task(start_consumer())` launches the Redis event consumer as a background coroutine that runs concurrently with request handling. After `yield` (shutdown), `consumer_task.cancel()` sends a cancellation signal; the `try/except asyncio.CancelledError` cleanly handles the task ending. `engine.dispose()` closes all database connections.

---

### `Backend/services/notification-service/app/services/consumer.py`

```python
CHANNEL_RE = re.compile(r'user:(\d+):notifs')
```
Regex to extract user_id from channel names like `user:42:notifs`. `(\d+)` captures one or more digits.

```python
async def start_consumer():
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.psubscribe('user:*:notifs')
```
`psubscribe` (pattern subscribe) subscribes to all channels matching `user:*:notifs` — where `*` is a Redis glob wildcard. This one subscription catches all per-user notification channels.

```python
    async for message in pubsub.listen():
        if message['type'] != 'pmessage':
            continue
        try:
            channel = message['channel']
            data    = json.loads(message['data'])
            asyncio.create_task(_process_event(channel, data))
        except Exception as e:
            logger.error(f'Consumer error: {e}')
```
`pubsub.listen()` is an async generator that yields messages. `type != 'pmessage'` skips subscription confirmation messages (type=`'psubscribe'`) and others. `asyncio.create_task()` processes each event concurrently — if notification processing is slow, it doesn't block the consumer loop from picking up the next event.

```python
async def _process_event(channel, data):
    match = CHANNEL_RE.match(channel)
    recipient_id = int(match.group(1))
    ...
    async with AsyncSessionLocal() as db:
        notif = await NotificationRepository.create(db, ...)
        if notif is None:
            return  # self-notification, skip
        actor     = await UserCacheRepository.get_by_id(db, actor_id)
        recipient = await UserCacheRepository.get_by_id(db, recipient_id)
    await deliver_notification(...)
```
Opens a new database session per event (not shared with any request context). `NotificationRepository.create()` returns `None` if `recipient_id == actor_id` (the `create` method has this guard). Uses `await` within `async with` to ensure the session is properly closed even if an exception occurs.

---

### `Backend/services/notification-service/app/services/delivery.py`

```python
async def deliver_notification(...):
    payload = {
        'id': notif_id, 'type': notif_type,
        'thread_id': thread_id, 'comment_id': comment_id,
        'actor': actor_username,
    }
    online = await is_user_online(recipient_id)
    if online:
        await publish(f'user:{recipient_id}:ws', payload)
    else:
        await send_notification_email(...)
```
`is_user_online` checks Redis for the presence of the TTL key `user:{id}:online`. If the key exists and hasn't expired, the user has an active WebSocket with a recent heartbeat. Publishing to `user:{id}:ws` puts the message in the channel that the notification WS handler is subscribed to — creating the WS → browser delivery chain.

---

### `Backend/services/notification-service/app/db/redis.py`

```python
ONLINE_TTL = 30  # seconds

async def set_user_online(user_id: int):
    r = await get_redis()
    await r.setex(f'user:{user_id}:online', ONLINE_TTL, '1')
```
`SETEX key seconds value` — set key with TTL in a single atomic Redis command. The 30-second TTL means if the WebSocket heartbeat stops (connection lost), the user is considered offline after 30 seconds. The heartbeat pings every 20 seconds to keep the TTL refreshed.

```python
async def is_user_online(user_id: int) -> bool:
    r = await get_redis()
    val = await r.get(f'user:{user_id}:online')
    return val is not None
```
If the key has expired or was deleted, `r.get()` returns `None`. The boolean conversion determines online status without needing to know the actual value (we set `'1'` as a placeholder).

---

### `Backend/services/notification-service/app/api/routes/websocket.py`

```python
@router.websocket('/ws/notifications')
async def notification_ws(ws: WebSocket, access_token: str = Cookie(default=None)):
    if not access_token:
        await ws.close(code=4001)
        return
```
`Cookie(default=None)` reads the `access_token` cookie from the WS upgrade request headers. Code 4001 is a custom application-level code (4000-4999 range is reserved for application use per WebSocket spec).

```python
    await ws.accept()
    await set_user_online(user_id)
    pubsub = await subscribe(f'user:{user_id}:ws')
    forward_task   = asyncio.create_task(_forward(ws, pubsub))
    heartbeat_task = asyncio.create_task(_heartbeat(ws, user_id))
```
`set_user_online` immediately — user is online as soon as the WS is accepted. Two concurrent tasks: `_forward` continuously listens to Redis and sends to WS; `_heartbeat` pings every 20 seconds.

```python
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get('type') == 'pong':
                await set_user_online(user_id)
    except WebSocketDisconnect:
        forward_task.cancel()
        heartbeat_task.cancel()
        await pubsub.unsubscribe()
        await set_user_offline(user_id)
```
`receive_text()` awaits any message from the browser. When `type == 'pong'` (response to server's ping), the online TTL is refreshed. On disconnect, all tasks are cancelled, Redis subscription is cleaned up, and the online key is deleted immediately (so delivery falls back to email right away).

---

### `Backend/services/notification-service/app/repositories/notification_repository.py`

```python
@staticmethod
async def create(db, recipient_id, actor_id, notif_type, thread_id=None, comment_id=None):
    if recipient_id == actor_id:
        return None
```
Self-notification guard at the repository level — the most reliable place to enforce this rule.

```python
@staticmethod
async def get_for_user(db, user_id, limit, offset):
    q = select(Notification).where(Notification.recipient_id == user_id)
    total  = await db.scalar(select(func.count()).select_from(q.subquery()))
    unread = await db.scalar(
        select(func.count()).where(
            Notification.recipient_id == user_id,
            Notification.is_read == False
        )
    )
    result = await db.execute(
        q.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all(), total, unread
```
Three queries per list request: total count, unread count, page of results. Returns all three so the frontend can display pagination and badge count in one API call.

---

## PART 5 — FRONTEND

### `Frontend/src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
```
`React` must be in scope for JSX transformation in React < 17; still imported for clarity. `ReactDOM` is from the new React 18 API (`react-dom/client`). `'./index.css'` is bundled by Vite and injects Tailwind CSS globally.

```jsx
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```
React 18's `createRoot` enables concurrent rendering. `getElementById('root')` targets the `<div id="root">` in `index.html`. `StrictMode` renders components twice in development to detect side effects — no effect in production.

---

### `Frontend/src/App.jsx`

```jsx
const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})
```
`staleTime: 30_000` — React Query won't refetch data within 30 seconds of a successful fetch. `retry: 1` — on failure, retry once before showing an error. Both are global defaults overridable per query.

```jsx
<QueryClientProvider client={qc}>
  <BrowserRouter>
    <Routes>
      <Route path='/login' element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route path='/feed' element={<FeedPage />} />
        <Route element={<RoleGuard minRole='moderator' />}>
          <Route path='/mod' element={<ModDashboard />} />
        </Route>
        <Route element={<RoleGuard minRole='admin' />}>
          <Route path='/admin' element={<AdminDashboard />} />
        </Route>
      </Route>
    </Routes>
  </BrowserRouter>
</QueryClientProvider>
```
`QueryClientProvider` wraps everything so all components can use `useQuery`, `useMutation`.
`BrowserRouter` uses the HTML5 History API (no hash in URLs).
Routes are **nested**: `<AuthGuard />` renders an `<Outlet />` only when authenticated, and nested routes render inside that outlet. `<RoleGuard>` is a further nested guard within `<AuthGuard>`.

---

### `Frontend/src/api/client.js`

```js
export const apiClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})
```
`withCredentials: true` — tells axios to include cookies (the JWT access_token) in every request, even to a different origin. Without this, the browser strips cookies from cross-origin requests.

```js
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        await apiClient.post('/api/auth/auth/refresh')
        return apiClient(original)
      } catch {
        localStorage.removeItem('threadix-auth')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)
```
Response interceptor with **automatic token refresh**. When any API call returns 401 (access token expired), the interceptor:
1. Sets `_retry = true` on the original request config to prevent infinite retry loops
2. Calls `POST /api/auth/auth/refresh` which reads the `refresh_token` cookie and issues new cookies
3. If refresh succeeds, retries the original request with `apiClient(original)` — the new cookies are automatically sent
4. If refresh fails (refresh token also expired after 7 days), clears the Zustand `threadix-auth` localStorage entry and redirects to `/login`
5. `return Promise.reject(err)` re-throws for non-401 errors so individual callers can handle them

---

### `Frontend/src/store/authStore.js`

```js
export const useAuthStore = create(persist(
  (set) => ({
    user:     null,
    isAuthed: false,
    setUser:  (u) => set({ user: u, isAuthed: true }),
    logout:   () => set({ user: null, isAuthed: false }),
  }),
  { name: 'threadix-auth' }
))
```
`create(persist(...))` — wraps Zustand's create with the persist middleware.
`{ name: 'threadix-auth' }` — the localStorage key. The full store state is serialized as JSON under this key.
`setUser` is called after a successful login or profile fetch to populate user data.
`logout` clears both user and isAuthed — any component subscribed to `isAuthed` re-renders and AuthGuard redirects to login.

---

### `Frontend/src/store/notifStore.js`

```js
export const useNotifStore = create((set) => ({
  unreadCount: 0,
  setCount:  (n) => set({ unreadCount: n }),
  increment: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  reset:     () => set({ unreadCount: 0 }),
}))
```
Not persisted (no `persist` wrapper). The unread count is fetched fresh on mount and updated via WebSocket events. `increment` uses the functional form of `set` (`(s) => ...`) to safely read the current state before updating — avoids stale closure bugs with concurrent increments.

---

### `Frontend/src/hooks/useWebSocket.js`

```js
export function useWebSocket({ channels, onMessage, enabled = true }) {
  const wsRef    = useRef(null)       // holds current WebSocket instance
  const retryRef = useRef()           // holds the setTimeout handle
  const delay    = useRef(1000)       // retry delay, starts at 1 second
  const channelsKey = channels.join(',')  // stable dependency for useCallback
```
`useRef` values persist across renders without causing re-renders. `channelsKey` is the stable string form of the channels array, used as the `useCallback` dependency.

```js
  const connect = useCallback(() => {
    if (!enabled || channels.length === 0) return
    const url = `${WS_BASE}/ws?channels=${channelsKey}`
    const ws  = new WebSocket(url)
    wsRef.current = ws
```
`useCallback` memoizes `connect` — it only changes when `channelsKey` or `enabled` changes. Without memoization, every render would create a new `connect` function, causing the `useEffect` to re-run continuously.

```js
    ws.onclose = () => {
      retryRef.current = setTimeout(() => {
        delay.current = Math.min(delay.current * 2, 30_000)
        connect()
      }, delay.current)
    }
    ws.onopen = () => { delay.current = 1000 }
```
Exponential backoff on disconnect: 1s → 2s → 4s → 8s → ... → max 30s. `ws.onopen` resets delay back to 1s so a reconnect starts fast again.

```js
  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])
```
`useEffect` runs `connect()` when the component mounts or `connect` changes. The cleanup function runs on unmount or before re-running: clears any pending retry timeout and closes the current WS. `?.close()` optional chaining handles the case where `wsRef.current` is null.

---

### `Frontend/src/guards/AuthGuard.jsx`

```jsx
export function AuthGuard() {
  const isAuthed = useAuthStore((s) => s.isAuthed)
  return isAuthed ? <Outlet /> : <Navigate to='/login' replace />
}
```
`useAuthStore((s) => s.isAuthed)` is a **selector** — the component only re-renders when `isAuthed` changes, not on every store update. `<Outlet />` renders the matched child route (e.g., FeedPage). `replace` in `<Navigate>` replaces the current history entry so the back button doesn't return to a protected route.

---

### `Frontend/src/guards/RoleGuard.jsx`

```jsx
const HIERARCHY = { member: 0, moderator: 1, admin: 2 }

export function RoleGuard({ minRole }) {
  const role = useAuthStore((s) => s.user?.role ?? 'member')
  return HIERARCHY[role] >= HIERARCHY[minRole]
    ? <Outlet />
    : <Navigate to='/feed' replace />
}
```
`??` nullish coalescing — if `user` is null (shouldn't happen inside AuthGuard, but defensive), defaults to `'member'`. Numeric comparison: `HIERARCHY["admin"] >= HIERARCHY["moderator"]` → `2 >= 1` → `true`, so admins can access moderator pages.

---

### `Frontend/src/lib/constants.js`

```js
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'
export const WS_BASE  = API_BASE.replace('http', 'ws')
```
`import.meta.env` is Vite's environment variable accessor. `VITE_` prefix is required for Vite to expose variables to the browser bundle. `replace('http', 'ws')` converts `http://...` to `ws://...` (and `https://...` to `wss://...` which preserves the `s`).

---

### `Frontend/src/lib/utils.js`

```js
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}
```
`clsx` builds a class string from any combination of strings, arrays, and objects (`{ 'text-red-500': isError }`). `twMerge` resolves Tailwind class conflicts — e.g., `cn('px-2 px-4')` → `'px-4'` (latter wins). Used throughout components as `className={cn('base-class', conditionalClass && 'extra-class')}`.

---

## PART 6 — INFRASTRUCTURE

### `docker-compose.yml` — Container Definitions

```yaml
postgres-auth:
  image: postgres:15
  environment:
    POSTGRES_DB: threadix_auth
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  ports:
    - "5433:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5
```
Maps host port 5433 to container port 5432 (default PostgreSQL port). The `healthcheck` uses `pg_isready` which polls the PostgreSQL server. Auth service `depends_on: postgres-auth: condition: service_healthy` waits until this health check passes before starting.

```yaml
redis:
  image: redis:7
  command: redis-server --requirepass threadix_redis_secret
  ports:
    - "6379:6379"
```
`--requirepass` sets a Redis password. All services connect via `redis://:threadix_redis_secret@redis:6379/0`. The `:` before the password in the URL is required (empty username).

```yaml
auth-service:
  build:
    context: ./services/auth-service
    dockerfile: Dockerfile
  depends_on:
    postgres-auth:
      condition: service_healthy
    redis:
      condition: service_started
  environment:
    DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres-auth:5432/threadix_auth
    REDIS_URL: redis://:threadix_redis_secret@redis:6379/0
    SECRET_KEY: c2b104ca1224fc46dcb2521a2a7d27b60a0ee6f13bdb5e268d6c4e0583376b3e
```
`postgresql+asyncpg://` — the asyncpg driver is required for SQLAlchemy async engine. `postgres-auth` is the Docker service name — resolved to the container's IP by Docker's embedded DNS within the `threadix` bridge network.

---

### `Backend/services/auth-service/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY . .
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```
`FROM python:3.11-slim` — minimal Python 3.11 image (no dev tools). `COPY pyproject.toml . && RUN pip install .` — installs dependencies before copying source code. This takes advantage of Docker layer caching: if `pyproject.toml` doesn't change, the install layer is cached and the build is faster. `alembic upgrade head && uvicorn` — runs migrations first, then starts the server.

### `Backend/services/thread-service/Dockerfile`

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```
No Alembic — thread-service manages schema via `create_all` in the lifespan function.

### `Frontend/Dockerfile`

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```
Multi-stage build: the first stage (`builder`) installs dependencies and runs `vite build` producing `/app/dist`. The second stage copies only the built files into a minimal nginx image — the final image contains no Node.js runtime, reducing size.

---

### `Frontend/vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```
`plugins: [react()]` enables JSX transformation and React Fast Refresh (hot module replacement). `alias: { '@': './src' }` registers `@` as an alias for the `src/` directory. Any `import X from '@/components/Foo'` resolves to `src/components/Foo`.

---

### `Frontend/tailwind.config.js`

```js
content: ['./index.html', './src/**/*.{js,jsx}'],
```
Tailwind scans these files to find class names used in the project. Only classes found here are included in the production CSS bundle. `{js,jsx}` covers all JavaScript component files.

---

### `Frontend/src/lib/constants.js`

```js
export const MAX_COMMENT_DEPTH = 4
export const PAGE_SIZE = 20
```
`MAX_COMMENT_DEPTH = 4` matches the backend constant. If the backend changes the limit, the frontend constant should be updated to match. `PAGE_SIZE = 20` is the default `limit` parameter for all paginated API calls.

---

## PART 7 — DATABASE SCHEMA (Full)

### auth-service: `users`

```sql
CREATE TABLE users (
    id           SERIAL PRIMARY KEY,
    email        VARCHAR UNIQUE NOT NULL,        -- login credential
    username     VARCHAR UNIQUE NOT NULL,        -- display name
    password_hash VARCHAR NOT NULL,              -- bcrypt output
    role         user_role_enum DEFAULT 'member',-- admin/moderator/member
    bio          VARCHAR(300),                   -- nullable, max 300 chars
    avatar_url   VARCHAR,                        -- Cloudinary CDN URL
    is_deleted   BOOLEAN DEFAULT FALSE,          -- soft delete flag
    created_at   TIMESTAMP DEFAULT now(),
    updated_at   TIMESTAMP DEFAULT now()
);
CREATE INDEX ix_users_email    ON users(email);
CREATE INDEX ix_users_username ON users(username);
```

### thread-service: all 8 tables

```sql
-- Denormalized user cache (synced via JWT on each request)
CREATE TABLE users_cache (
    id         INTEGER PRIMARY KEY,   -- same as auth.users.id
    username   VARCHAR(50) UNIQUE NOT NULL,
    avatar_url VARCHAR,
    role       VARCHAR,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE tags (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(30) UNIQUE NOT NULL,
    is_seeded  BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users_cache(id)
);

CREATE TABLE threads (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users_cache(id),
    title         VARCHAR(200) NOT NULL,
    description   TEXT NOT NULL,
    media_urls    TEXT[],              -- PostgreSQL native array
    like_count    INTEGER DEFAULT 0,  -- denormalized counter
    view_count    INTEGER DEFAULT 0,  -- denormalized counter
    comment_count INTEGER DEFAULT 0,  -- denormalized counter
    is_deleted    BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE thread_tags (
    thread_id INTEGER REFERENCES threads(id) ON DELETE CASCADE,
    tag_id    INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (thread_id, tag_id)
);

CREATE TABLE comments (
    id         SERIAL PRIMARY KEY,
    thread_id  INTEGER REFERENCES threads(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users_cache(id),
    parent_id  INTEGER REFERENCES comments(id) ON DELETE SET NULL,
    depth      INTEGER NOT NULL DEFAULT 0,
    content    TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE likes (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users_cache(id),
    thread_id  INTEGER REFERENCES threads(id),
    comment_id INTEGER REFERENCES comments(id),
    UNIQUE (user_id, thread_id),   -- one like per user per thread
    UNIQUE (user_id, comment_id)   -- one like per user per comment
);

CREATE TABLE user_tag_affinity (
    user_id INTEGER REFERENCES users_cache(id),
    tag_id  INTEGER REFERENCES tags(id),
    score   FLOAT NOT NULL,
    PRIMARY KEY (user_id, tag_id)
);
CREATE INDEX ix_affinity_user ON user_tag_affinity(user_id);
```

### notification-service: 2 tables

```sql
CREATE TABLE users_cache (
    id         INTEGER PRIMARY KEY,
    username   VARCHAR(50) NOT NULL,
    email      VARCHAR NOT NULL,     -- needed for fallback email delivery
    avatar_url VARCHAR,
    role       VARCHAR,
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE notifications (
    id           SERIAL PRIMARY KEY,
    recipient_id INTEGER NOT NULL,   -- who receives this notification
    actor_id     INTEGER NOT NULL,   -- who triggered it
    type         notif_type_enum,    -- reply/mention/like/comment
    thread_id    INTEGER,
    comment_id   INTEGER,
    is_read      BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT now()
);
CREATE INDEX ix_notif_recipient ON notifications(recipient_id);
CREATE INDEX ix_notif_user_time ON notifications(recipient_id, created_at DESC);
```

---

## PART 8 — ALEMBIC MIGRATIONS (Auth Service)

The auth service is the only service using Alembic. The 4 migration files tell the complete schema evolution story:

```
1ac2d4dde69a_create_users_table.py
  → Creates the initial `users` table with: id, email, username, password_hash,
    is_deleted, created_at, updated_at

2c06a3338c82_add_role_column.py
  → ALTER TABLE users ADD COLUMN role user_role_enum DEFAULT 'member'
  → Creates the PostgreSQL ENUM type: admin, moderator, member

d36ed3786a93_add_avatar_url_column.py
  → ALTER TABLE users ADD COLUMN avatar_url VARCHAR

(Final state in models.py adds bio column implicitly via create_all on fresh DBs)
```

`alembic upgrade head` runs all unapplied migrations in order using the `alembic_version` table to track which migrations have been applied.

---

## PART 9 — PLANNED IMPROVEMENTS (Implementation Guide)

### Email Notifications (`notification-service/app/services/email_service.py`)

Currently a no-op stub — delivery is silently skipped when users are offline. To implement:

1. Choose a provider and add it to `pyproject.toml`:
   - **Resend** → `"resend>=2.0"`
   - **SendGrid** → `"sendgrid>=6.11"`
   - **AWS SES** → `"boto3>=1.34"`

2. Add the API key to `notification-service/app/core/config.py`:
   ```python
   EMAIL_API_KEY: str = ''
   FROM_EMAIL: str = 'noreply@threadix.app'
   ```

3. Add it to `notification-service/.env`:
   ```
   EMAIL_API_KEY=your_key_here
   FROM_EMAIL=your_verified_sender@example.com
   ```

4. Replace the stub in `email_service.py` with the actual send call. Example using Resend:
   ```python
   import resend
   resend.api_key = settings.EMAIL_API_KEY

   async def send_notification_email(recipient_email, actor_username, notif_type, thread_id):
       if not recipient_email or not settings.EMAIL_API_KEY:
           return
       body = f'{actor_username} triggered a {notif_type} on thread #{thread_id}.'
       resend.Emails.send({
           "from": settings.FROM_EMAIL,
           "to": recipient_email,
           "subject": "New notification on Threadix",
           "text": body,
       })
   ```

No other files need changing — `delivery.py` already calls `send_notification_email()`.

---

### Password Reset Email (`auth-service/app/services/email_services.py`)

Currently `send_reset_email()` only logs the token to console. The reset flow itself works — `POST /auth/reset-password` with the token resets the password correctly. To send the token by email instead of logging it, replace `email_services.py` implementation with the same email provider used above.

The reset link format to include in the email:
```
http://localhost:5173/reset-password?token={token}
```

---

### Forgot Password Flow (Future)

The `/auth/forgot-password` endpoint and `ForgotPasswordPage` have been **removed** since they depended on email delivery. To re-add self-service password reset:

1. Implement email delivery as described above
2. Re-add the `request_reset(db, email)` function to `password_services.py`
3. Re-add `POST /auth/forgot-password` route to `auth/routes/auth.py`
4. Re-add `ForgotPasswordPage.jsx` and its route in `App.jsx`
5. Re-add the "Forgot password?" link in `LoginPage.jsx`
