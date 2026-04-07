# Threadix — High-Level Design (HLD)

---

## 1. What is Threadix?

Threadix is a full-stack discussion platform. Users create threaded discussions, post nested comments, like content, follow topics, receive real-time notifications (via WebSocket and email), and access role-gated dashboards. The system is built as a microservices application: one React frontend, an API gateway, three backend services, a shared Redis instance, and three isolated PostgreSQL databases — all orchestrated with Docker Compose.

---

## 2. System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          User's Browser                                  │
│            React 18 + Vite + Zustand + React Query (JSX)                │
│                          localhost:5173                                  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  HTTP (axios, withCredentials)
                                │  WebSocket (native browser API)
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          API Gateway                                     │
│               FastAPI + httpx + websockets library                       │
│                          localhost:8080                                  │
│                                                                          │
│  /api/auth/*           ──────────────────────► auth-service:8000        │
│  /api/threads/*                                                          │
│  /api/search/*         ──────────────────────► thread-service:8001      │
│  /api/tags/*                                                             │
│  /api/mentions/*       ──────────────────────► thread-service:8001      │
│  /api/notifications/*  ──────────────────────► notification-service:8002│
│  /ws/notifications     ──────────────────────► notification-service:8002│
│  /ws, /ws/*            ──────────────────────► thread-service:8001      │
└────────────┬─────────────────┬────────────────────────┬─────────────────┘
             │                 │                        │
             ▼                 ▼                        ▼
┌────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐
│  Auth Service  │   │  Thread Service   │   │  Notification Service    │
│    :8000       │   │     :8001         │   │        :8002             │
│                │   │                   │   │                          │
│  FastAPI       │   │  FastAPI          │   │  FastAPI                 │
│  bcrypt        │   │  Cloudinary       │   │  Redis Consumer          │
│  JWT           │   │  Rate Limiting    │   │  WS presence heartbeat   │
│  Alembic       │   │  Pub/Sub publish  │   │  (email: planned)        │
└──────┬─────────┘   └────────┬──────────┘   └────────────┬─────────────┘
       │                      │                           │
       ▼                      │              ┌────────────┴─────────────────┐
┌────────────────┐            │              │         Redis :6379           │
│   Postgres     │            │              │                               │
│  (Auth DB)     │            │              │  refresh:{uid}  (token store) │
│  :5433         │            │              │  rl:{op}:{uid}  (rate limit)  │
│                │            │              │  user:{uid}:online (presence) │
│  users         │            │              │                               │
│  (1 table)     │            │              │  Pub/Sub Channels:            │
└────────────────┘            │              │  user:*:notifs  (thread→notif)│
                              │              │  user:*:ws      (notif→client)│
                    ┌─────────┘              │  thread:*:comments            │
                    │                        │  thread:*:likes               │
                    ▼                        │  threads (new thread events)  │
          ┌──────────────────┐               └──────────────────────────────┘
          │    Postgres       │
          │  (Thread DB)      │              ┌──────────────────────────────┐
          │  :5434            │              │    Postgres                   │
          │                   │              │  (Notification DB)            │
          │  users_cache      │              │    :5435                      │
          │  threads          │              │                               │
          │  comments         │              │  users_cache                  │
          │  likes            │              │  notifications                │
          │  tags             │              │  (2 tables)                   │
          │  thread_tags      │              └──────────────────────────────┘
          │  user_tag_affinity│
          │  (8 tables)       │
          └──────────────────┘
```

---

## 3. Service Responsibilities

| Service | Port | Owns | Primary Duty |
|---------|------|------|-------------|
| **Frontend** | 5173 | — | React SPA: renders UI, manages routing, auth state, data fetching, admin/mod dashboards |
| **Gateway** | 8080 | — | Single entry point: HTTP proxy + WebSocket bidirectional proxy |
| **Auth Service** | 8000 | `threadix_auth` DB | Registration, login, JWT issuance, token rotation, profile, role management |
| **Thread Service** | 8001 | `threadix_thread` DB | Thread + comment CRUD, likes, tags, search, feed ranking, Redis pub/sub publish |
| **Notification Service** | 8002 | `threadix_notification` DB | Receive Redis events, persist notifications, route to WebSocket or email |
| **Redis** | 6379 | In-memory + pub/sub | Refresh token store, rate limit counters, online presence, event bus |

---

## 4. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 18 + Vite | Fast refresh, JSX, optimized builds |
| State | Zustand | Lightweight, persisted auth state |
| Server state | React Query v5 | Caching, pagination, mutations |
| Routing | React Router v6 | Nested routes, outlet-based guards |
| Styling | Tailwind CSS v3 | Utility-first, no custom CSS overhead |
| HTTP client | axios | Interceptors for 401 auto-refresh + retry, withCredentials |
| Backend | FastAPI (Python) | Async, automatic OpenAPI docs, Pydantic validation |
| DB ORM | SQLAlchemy async | Typed models, async queries |
| Migrations | Alembic (auth only) | Schema versioning for auth service |
| Password | bcrypt | Salted hash, resistant to rainbow tables |
| Auth tokens | JWT (python-jose) | Stateless identity, shared between services |
| HTTP proxy | httpx | Async HTTP client inside gateway |
| WS proxy | websockets library | Full-duplex async WebSocket |
| File storage | Cloudinary CDN | Managed media upload + delivery |
| Cache/PubSub | Redis (redis.asyncio) | Speed, pub/sub, TTL-based presence |
| Containers | Docker Compose | Reproducible local environment |

---

## 5. Data Flow Patterns

### Pattern A — Standard HTTP request (e.g., list threads)

```
Browser
  → GET /api/threads/?offset=0&limit=20
  → axios sends httpOnly cookies automatically (withCredentials: true)

Gateway
  → Strips host/content-length headers
  → Forwards to http://thread-service:8001/threads/?offset=0&limit=20
  → Thread service checks JWT cookie, queries PostgreSQL
  → Returns JSON list

Gateway
  → Strips content-encoding/transfer-encoding/content-length from response
  → Passes status + body back to browser
```

### Pattern B — Login / token issuance

```
Browser
  → POST /api/auth/auth/login  {email, password}

Auth Service
  → lookup user by email
  → bcrypt.checkpw(submitted_password, stored_hash)
  → Build JWT claims: sub, role, username, avatar_url, email
  → access_token  = JWT(claims, exp=+15 min, HS256)
  → refresh_token = JWT({sub: user_id}, exp=+7 days, HS256)
  → Redis SET refresh:{user_id} = sha256(refresh_token)  TTL=7 days
  → set-cookie: access_token (httpOnly), refresh_token (httpOnly)
  → 200 OK

Browser
  → Calls GET /user/profile to hydrate authStore
  → Zustand persists user to localStorage
  → React Router navigates to /feed
```

### Pattern B2 — Automatic token refresh (401 interceptor)

```
Browser
  → Any API call returns 401 (access_token expired)

Axios interceptor (client.js)
  → Sets _retry flag on the original request
  → POST /api/auth/auth/refresh
  → Auth service verifies refresh_token cookie
  → Issues new access_token + refresh_token cookies
  → Axios retries the original request automatically
  → If refresh also fails (7-day token expired)
      → Clear Zustand localStorage ('threadix-auth')
      → Redirect to /login
```

### Pattern C — Real-time notification (like a thread)

```
Browser
  → POST /api/threads/5/like

Thread Service
  → INSERT INTO likes (user_id, thread_id)
  → UPDATE threads SET like_count = like_count + 1  (atomic, same transaction)
  → UPDATE user_tag_affinity (UPSERT score += 2.0) for each tag of thread
  → Redis PUBLISH user:{thread_owner_id}:notifs
      {"event":"like","actor_id":42,"thread_id":5}
  → Return 200 immediately (notification is fire-and-forget)

Notification Service (background)
  → Consumer already psubscribed to user:*:notifs
  → asyncio.create_task(_process_event(channel, data))
  → INSERT INTO notifications (recipient_id, actor_id, type="like", thread_id=5)
  → Lookup actor username, recipient email from users_cache
  → Check Redis: EXISTS user:{owner_id}:online
      YES → Redis PUBLISH user:{owner_id}:ws {id, type, thread_id, actor}
              → WS handler forwards to browser WebSocket connection
              → NotifBell increments unreadCount in notifStore
      NO  → email delivery not implemented (logged, silently skipped)
```

### Pattern D — Profile update with cross-service sync

```
Browser
  → PUT /api/auth/user/profile (multipart: username, bio, avatar file)

Auth Service
  → Upload avatar to Cloudinary (overwrite=True, invalidate=True)
  → Update user row in threadix_auth DB
  → Re-issue JWT cookies with fresh claims (avatar_url, username)
  → Publish to Redis Stream: XADD user_profile_updates {user_id, username, avatar_url}
  → Return updated profile

Thread Service (background worker)
  → _profile_sync_worker() runs as asyncio.create_task in lifespan
  → XREAD BLOCK 5000 on user_profile_updates stream
  → On new message: UPDATE users_cache SET username=..., avatar_url=... WHERE id=...
  → users_cache now has fresh data for thread/comment author display
```

### Pattern E — File upload with media

```
Browser
  → POST /api/threads/ (multipart/form-data)
    Fields: title, description, tag_ids, files[]

Thread Service
  → Validate MIME type (image/*, video/*)
  → Validate file size (images ≤ 5 MB, videos ≤ 50 MB)
  → cloudinary.uploader.upload(file.file)  ← synchronous SDK call
  → Returns {"secure_url": "https://res.cloudinary.com/..."}
  → Store URL in threads.media_urls (ARRAY column)
  → 201 Created with thread JSON including media_urls
```

### Pattern E — Personalized feed

```
Browser
  → GET /api/threads/feed?limit=20&offset=0

Thread Service
  → Execute raw SQL (personalized feed query):
    SELECT t.id, COALESCE(SUM(uta.score), 0) AS affinity_score
    FROM threads t
    LEFT JOIN thread_tags tt  ON tt.thread_id = t.id
    LEFT JOIN user_tag_affinity uta
      ON uta.tag_id = tt.tag_id AND uta.user_id = :uid
    WHERE t.is_deleted = false
    GROUP BY t.id
    ORDER BY affinity_score DESC, t.created_at DESC
    LIMIT :lim OFFSET :off
  → Threads the user has engaged with appear first
  → Unseen topics appear in chronological order at bottom
  → Return sorted list
```

---

## 6. Authentication & Authorization Architecture

### JWT design

```
Access token (15 minutes):
{
  "sub": "42",           ← user ID (string)
  "username": "alice",
  "role": "moderator",
  "avatar_url": "https://res.cloudinary.com/...",
  "email": "alice@example.com",
  "exp": 1710000000
}

Refresh token (7 days):
{
  "sub": "42",
  "exp": 1710604800
}
```

### Token rotation (prevents refresh token reuse)

```
On POST /auth/refresh:
  1. Decode submitted refresh_token → get user_id
  2. sha256(submitted) ──compare──► Redis GET refresh:{user_id}
  3. If mismatch → STOLEN TOKEN — reject, both tokens invalidated
  4. Redis DEL refresh:{user_id}         ← old token invalidated
  5. Create new access_token + refresh_token
  6. Redis SET refresh:{user_id} = sha256(new_refresh)  TTL=7d
  7. Set new cookies
```

### Role hierarchy

```
member (0) < moderator (1) < admin (2)

Enforcement:
  - auth-service: require_role(["admin"]) decorator — checks JWT.role
  - thread-service: require_role("admin", "moderator") dependency
  - frontend: RoleGuard checks HIERARCHY[user.role] >= HIERARCHY[minRole]
```

### Zero inter-service auth calls

Each downstream service decodes the JWT locally using the **shared SECRET_KEY**. No HTTP call to auth-service is needed per request. The JWT contains all needed identity claims.

---

## 7. Denormalization Strategy

To avoid expensive JOIN queries on hot read paths, several counters are stored redundantly:

| Denormalized field | Where stored | Updated when | Atomic? |
|-------------------|-------------|--------------|---------|
| `threads.like_count` | threads table | Like/unlike | Yes (`like_count + 1`) |
| `threads.view_count` | threads table | GET /threads/{id} | Yes |
| `threads.comment_count` | threads table | Create/delete comment | Yes |
| `comments.like_count` | comments table | Like/unlike comment | Yes |
| `user_tag_affinity.score` | affinity table | Like, comment | Yes (UPSERT) |
| `users_cache.username/role` | thread & notif DBs | Every request (JWT upsert) + Redis stream | Yes (ON CONFLICT) |

All counter updates use database-side arithmetic (`col = col + 1`) — never read-increment-write in Python, which would create race conditions under concurrent requests.

---

## 8. WebSocket Architecture

```
Two independent WebSocket upgrade paths through the gateway:

Path 1: /ws/notifications  →  notification-service:8002/ws/notifications
  • One connection per logged-in user
  • Dedicated to notification delivery
  • Server sends ping every 20s; client must pong to maintain TTL
  • Online presence: Redis key user:{id}:online  TTL=30s

Path 2: /ws  →  thread-service:8001/ws?channels=...
  • Query string specifies channels to subscribe to
  • Channels: threads, thread:{id}:comments, thread:{id}:likes
  • Multiple subscriptions in one connection (comma-separated)
  • Used by FeedPage, ThreadDetailPage for live updates

Gateway bidirectional proxy:
  • asyncio.wait(FIRST_COMPLETED) on [client→backend, backend→client] tasks
  • When either side closes, cancels the other task immediately
```

---

## 9. Redis Pub/Sub Event Bus

```
Publisher              Channel / Stream             Subscriber
─────────────────────────────────────────────────────────────────
thread-service    →  threads              →  FeedPage WS client
thread-service    →  thread:{id}:comments →  ThreadDetailPage WS client
thread-service    →  thread:{id}:likes    →  ThreadDetailPage WS client
thread-service    →  user:{id}:notifs     →  Notification service consumer
                                              (psubscribed to user:*:notifs)
notif-service     →  user:{id}:ws         →  Notification WS handler
                                              → browser WebSocket
auth-service      →  user_profile_updates →  Thread service background worker
                     (Redis Stream XADD)     (XREAD BLOCK consumer)
```

---

## 10. Docker Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                  Docker network: threadix (bridge)                │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ postgres │  │ postgres │  │   postgres   │  │    redis    │  │
│  │  -auth   │  │ -thread  │  │  -notif      │  │             │  │
│  │  :5432   │  │  :5432   │  │  :5432       │  │   :6379     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └──────┬──────┘  │
│       │             │               │                  │          │
│  ┌────┴─────┐  ┌────┴─────┐  ┌──────┴───────┐         │          │
│  │   auth   │  │  thread  │  │  notification│         │          │
│  │ service  │  │ service  │  │   service    │◄────────┤          │
│  │  :8000   │  │  :8001   │  │    :8002     │         │          │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘         │          │
│       │             │               │                  │          │
│       └─────────────┴───────────────┴──────────────────┘          │
│                              │                                     │
│                      ┌───────┴──────┐                             │
│                      │   gateway    │                             │
│                      │    :8080     │                             │
│                      └───────┬──────┘                             │
│                              │                                     │
│                      ┌───────┴──────┐                             │
│                      │  frontend    │                             │
│                      │    :5173     │                             │
│                      └──────────────┘                             │
└──────────────────────────────────────────────────────────────────┘

Host port mappings (dev access):
  8080 → gateway          5173 → frontend
  8000 → auth-service     8001 → thread-service    8002 → notification-service
  5433 → postgres-auth    5434 → postgres-thread   5435 → postgres-notification
  6379 → redis
```

---

## 11. Service Startup Sequence

```
docker compose up:

1. postgres-auth, postgres-thread, postgres-notification, redis
   → Start in parallel
   → Health checks: pg_isready, redis-cli ping

2. auth-service, thread-service, notification-service
   → Start after their databases are healthy
   → auth-service:       runs `alembic upgrade head` (4 migrations)
   → thread-service:     runs Base.metadata.create_all(), seeds default tags
   → notification-service: runs Base.metadata.create_all(), launches Redis consumer task

3. gateway
   → Starts after all three services start
   → Creates shared httpx.AsyncClient(timeout=30.0)

4. frontend
   → Starts independently (no backend dependency for container start)
   → nginx serves built assets or Vite runs dev server
```

---

## 12. Security Model

| Threat | Mitigation |
|--------|-----------|
| Password breach | bcrypt with per-user salt (never stored plaintext) |
| JWT theft | httpOnly cookies (JS cannot read), 15-minute access token lifetime |
| Refresh token reuse (stolen token) | SHA-256 rotation: reuse detected → session invalidated |
| CSRF | `SameSite` cookies + CORS origin whitelist |
| Unauthorized access | JWT decoded locally per service + role hierarchy |
| API abuse | Redis rate limiting per (user, operation) |
| SQL injection | SQLAlchemy parameterized queries (no raw string concat) |
| File upload attacks | MIME type check + file size limit before storage |
| Self-notification | `NotificationRepository.create()` returns None if recipient == actor |

---

## 13. Complete API Surface (Quick Reference)

### Auth Service

| Method | Path | Auth | Action |
|--------|------|------|--------|
| POST | /auth/register | — | Register new user |
| POST | /auth/login | — | Login, set cookies |
| POST | /auth/refresh | cookie | Rotate access + refresh tokens |
| POST | /auth/logout | cookie | Delete tokens, clear cookies |
| POST | /auth/reset-password | — | Validate token, update password |
| GET | /user/profile | cookie | Get own profile |
| PUT | /user/profile | cookie | Update username, bio, avatar |
| PUT | /user/change-password | cookie | Change password |
| GET | /user/{username} | — | Get any user's public profile |
| GET | /user/list | admin | Paginated user list |
| PUT | /user/role/{username} | admin | Change role by username |
| DELETE | /user/delete/{user_id} | admin | Soft-delete user |

### Thread Service

| Method | Path | Auth | Action |
|--------|------|------|--------|
| GET | /threads/feed | cookie | Personalized feed |
| GET | /threads/ | — | All threads, chronological |
| POST | /threads/ | cookie | Create thread (multipart + media) |
| GET | /threads/{id} | cookie | Get thread (increments views) |
| PATCH | /threads/{id} | author/admin | Edit thread |
| DELETE | /threads/{id} | author/mod/admin | Soft-delete thread |
| GET | /threads/stats | — | Thread + comment counts |
| POST | /threads/{id}/like | cookie | Toggle like |
| GET | /threads/{id}/comments/ | — | Top-level comments |
| POST | /threads/{id}/comments/ | cookie | Create comment |
| GET | /threads/{id}/comments/{cid}/children | — | Load child replies |
| PATCH | /threads/{id}/comments/{cid} | author/admin | Edit comment |
| DELETE | /threads/{id}/comments/{cid} | author/mod/admin | Delete comment |
| POST | /threads/{id}/comments/{cid}/like | cookie | Toggle comment like |
| GET | /search/threads?q= | — | Full-text search |
| GET | /search/users?q= | cookie | @mention autocomplete |
| GET | /tags/ | — | List all tags |
| POST | /tags/ | cookie | Create tag |
| WS | /ws?channels= | cookie | Live thread/like/comment feed |

### Notification Service

| Method | Path | Auth | Action |
|--------|------|------|--------|
| GET | /notifications/ | cookie | List notifications |
| GET | /notifications/unread-count | cookie | Unread count |
| PATCH | /notifications/{id}/read | cookie | Mark one read |
| PATCH | /notifications/read-all | cookie | Mark all read |
| WS | /ws/notifications | cookie | Live notification stream |

---

## 14. Planned Improvements

| Feature | Description |
|---------|-------------|
| **Email notifications** | Integrate a transactional email provider (SendGrid, Resend, or AWS SES) in `notification-service/app/services/email_service.py`. When a user is offline, notifications currently fall back to a no-op log. The delivery wiring is already in place — only the send call needs implementation. |
| **Password reset email** | Wire `auth-service/app/services/email_services.py` to an email provider so `POST /auth/reset-password` can be initiated self-service. Currently the reset token is only logged to console (development use). |
| **Notification service horizontal scaling** | Replace Redis `PSUBSCRIBE` with Redis Streams + consumer groups so multiple notification-service instances can share the load without duplicate deliveries. |
| **Access token blacklist** | On logout, add the access token's `jti` to a short-lived Redis set to prevent use of tokens that haven't expired yet. |
| **Notification cleanup** | Add a scheduled job to delete notifications older than 90 days to prevent the notifications table growing unboundedly. |
| **Push notifications** | Add Web Push API support (via VAPID keys) for notifications even when the browser tab is closed. |
| **Notification preferences** | Add a `notification_preferences` table so users can opt out of specific notification types (e.g., disable like notifications). |

---

## 15. Testing

| Service | Test File(s) | Tests | Coverage |
|---------|-------------|-------|----------|
| **Auth Service** | `test_hashing.py`, `test_security.py`, `test_schemas.py`, `test_auth_service.py` | 27 | Hashing (4), JWT create/decode/expiry (5), schema validation (10), auth logic — register/login/refresh/logout (8) |
| **Thread Service** | `test_thread_permissions.py`, `test_comment_permissions.py`, `test_schemas.py` | 29 | Thread edit/delete permission matrix (9), comment edit/delete permission matrix (11), schema validation (9) |
| **Notification Service** | `test_schemas.py`, `test_notification_repository.py`, `test_delivery.py`, `test_consumer.py` | 15 | Schema validation (4), self-notification guard + CRUD (4), delivery routing online/offline (3), channel regex (4) |
| **Gateway** | `test_routing.py` | 9 | All 6 route mappings, unknown route 404, upstream down 503 |
| **Total** | **12 test files** | **80** | All services covered |

Tests use `pytest` + `pytest-asyncio` with `unittest.mock` (AsyncMock, patch). No live database or Redis required — all external dependencies are mocked.

---

## 16. Role-Based Permission Model

| Action | Owner | Moderator | Admin |
|--------|-------|-----------|-------|
| Edit own thread/comment | ✅ | ✅ (own only) | ✅ |
| Edit others' thread/comment | ❌ | ❌ | ✅ |
| Delete own thread/comment | ✅ | ✅ (own only) | ✅ |
| Delete others' thread/comment | ❌ | ✅ | ✅ |
| Access admin dashboard (`/admin`) | ❌ | ❌ | ✅ |
| Access mod dashboard (`/mod`) | ❌ | ✅ | ✅ |
| Manage user roles | ❌ | ❌ | ✅ |
| Delete users | ❌ | ❌ | ✅ |

**Frontend enforcement:** `canEdit = isOwner || isAdmin`, `canDelete = isOwner || isModerator` (where `isModerator` includes admin via `useRole()` hook).  
**Backend enforcement:** `update_thread`/`update_comment` check `user.role != 'admin'`; `delete_thread`/`delete_comment` check `user.role not in ('admin', 'moderator')`.
