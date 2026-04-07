# Threadix

A full-stack discussion forum built with a **microservices architecture**. Users can create threads, post nested comments, like content, mention others with `@username`, and receive real-time notifications via WebSocket.

---

## Architecture Overview

```
Browser (React + Vite)
        │
        ▼
  API Gateway :8080 (FastAPI + httpx)
    ├── /api/auth/*          → Auth Service :8000
    ├── /api/threads/*       → Thread Service :8001
    ├── /api/search/*        → Thread Service :8001
    ├── /api/tags/*          → Thread Service :8001
    ├── /api/notifications/* → Notification Service :8002
    ├── /ws/notifications    → Notification Service :8002  (WebSocket)
    └── /ws/*                → Thread Service :8001        (WebSocket)
```

All services communicate through a shared **Redis** instance for pub/sub events, and each service has its own **PostgreSQL** database. The entire stack runs in Docker containers on a single `threadix` bridge network.

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 (one per service) |
| ORM | SQLAlchemy 2 (async) + Alembic migrations |
| Cache / Pub-Sub | Redis 7 |
| Auth | JWT (HS256) — httpOnly cookies, access + refresh tokens |
| File Uploads | Cloudinary (avatars, thread media) |
| Rate Limiting | SlowAPI (thread service) |
| Package Manager | uv |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18 (Vite, JSX) |
| State | Zustand (persisted to localStorage) |
| Data Fetching | TanStack Query v5 |
| Styling | Tailwind CSS |
| HTTP Client | Axios (with auto-refresh interceptor) |
| Real-time | Native WebSocket with exponential backoff reconnect |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Proxy | FastAPI gateway (Python) — nginx config included as reference |

---

## Features

- **Authentication** — Register, login, logout, email verification, password reset, refresh token rotation
- **Threads** — Create, edit, delete, like/unlike with tag filtering and full-text search
- **Comments** — Nested (tree) comments with infinite depth, likes, `@mention` support
- **Notifications** — Real-time WebSocket delivery when online; persistent notification history; unread badge
- **Profiles** — Avatar upload (Cloudinary), username/email editing with JWT re-issue, change password
- **Role-Based Access Control** — Three roles: `member`, `moderator`, `admin`
  - **Members** can edit/delete their own content
  - **Moderators** can delete any thread or comment (but not edit others' content)
  - **Admins** can edit and delete any thread or comment
- **Dashboards** — Admin dashboard (user management, thread stats) and moderator dashboard (thread/comment moderation)
- **Real-time Updates** — Thread detail pages receive live comment and like events via WebSocket

---

## Project Structure

```
Threadix/
├── docker-compose.yml              # Orchestrates all services
├── HLD.md                          # High-Level Design document
├── LLD.md                          # Low-Level Design document (line-by-line)
│
├── Backend/
│   ├── gateway/                    # API Gateway (FastAPI + httpx proxy)
│   │   ├── app/main.py             # All routing logic (~150 lines)
│   │   ├── nginx.conf              # Alternative nginx config (reference)
│   │   ├── tests/                  # 9 routing tests
│   │   └── GATEWAY_DOCUMENTATION.md
│   │
│   └── services/
│       ├── auth-service/           # Authentication & user management
│       │   ├── app/
│       │   │   ├── api/routes/     # HTTP endpoints
│       │   │   ├── core/           # JWT, hashing, config
│       │   │   ├── db/             # Models, schemas, database
│       │   │   ├── repositories/   # SQL queries
│       │   │   ├── services/       # Business logic
│       │   │   └── utils/          # Logger
│       │   ├── alembic/            # Database migrations
│       │   ├── tests/              # 27 tests
│       │   └── AUTH_SERVICE_DOCUMENTATION.md
│       │
│       ├── thread-service/         # Threads, comments, likes, tags, search
│       │   ├── app/                # Same structure as auth-service
│       │   ├── alembic/
│       │   ├── tests/              # 29 tests
│       │   └── THREAD_SERVICE_DOCUMENTATION.md
│       │
│       └── notification-service/   # Event-driven notification delivery
│           ├── app/
│           ├── alembic/
│           ├── tests/              # 15 tests
│           └── NOTIFICATION_SERVICE_DOCUMENTATION.md
│
└── Frontend/
    └── src/
        ├── api/                    # Axios client + API modules
        ├── components/             # React components (thread, comment, layout, notification)
        ├── guards/                 # AuthGuard, RoleGuard
        ├── hooks/                  # useAuth, useRole, useWebSocket
        ├── pages/                  # Page components (Feed, ThreadDetail, Profile, Admin/Mod dashboards)
        ├── store/                  # Zustand stores (auth, notifications)
        └── App.jsx                 # Router + layout
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/anushkasingh0305/threadix.git
cd threadix
```

### 2. Create environment files

Each backend service needs a `.env` file. Create them with the following content:

**`Backend/services/auth-service/.env`**
```env
DATABASE_URL=postgresql+asyncpg://threadix_auth:threadix_auth_secret@postgres-auth:5432/threadix_auth
REDIS_URL=redis://:threadix_redis_secret@redis:6379/0
JWT_SECRET_KEY=c2b104ca1224fc46dcb2521a2a7d27b60a0ee6f13bdb5e268d6c4e0583376b3e
JWT_ALGORITHM=HS256
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
```

**`Backend/services/thread-service/.env`**
```env
DATABASE_URL=postgresql+asyncpg://threadix_thread:threadix_thread_secret@postgres-thread:5432/threadix_thread
REDIS_URL=redis://:threadix_redis_secret@redis:6379/0
JWT_SECRET_KEY=c2b104ca1224fc46dcb2521a2a7d27b60a0ee6f13bdb5e268d6c4e0583376b3e
JWT_ALGORITHM=HS256
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
```

**`Backend/services/notification-service/.env`**
```env
DATABASE_URL=postgresql+asyncpg://threadix_notification:threadix_notification_secret@postgres-notification:5432/threadix_notification
REDIS_URL=redis://:threadix_redis_secret@redis:6379/0
JWT_SECRET_KEY=c2b104ca1224fc46dcb2521a2a7d27b60a0ee6f13bdb5e268d6c4e0583376b3e
JWT_ALGORITHM=HS256
```

### 3. Build and start all services

```bash
docker compose up --build -d
```

This starts:
- 3 PostgreSQL databases (ports 5433, 5434, 5435)
- 1 Redis instance (port 6380)
- Auth service (port 8000)
- Thread service (port 8001)
- Notification service (port 8002)
- API Gateway (port 8080)
- Frontend (port 5173)

### 4. Run database migrations (auth and thread services)

```bash
docker compose exec auth-service uv run alembic upgrade head
docker compose exec thread-service uv run alembic upgrade head
```

The notification service auto-creates its tables at startup — no migration needed.

### 5. Open the app

Navigate to **http://localhost:5173** in your browser.

---

## Running Tests

Tests run locally using `pytest` — no Docker services required.

```bash
# Auth service (27 tests)
cd Backend/services/auth-service
uv run pytest tests/ -v

# Thread service (29 tests)
cd Backend/services/thread-service
uv run pytest tests/ -v

# Notification service (15 tests)
cd Backend/services/notification-service
uv run pytest tests/ -v

# Gateway (9 tests)
cd Backend/gateway
uv run pytest tests/ -v
```

**Total: 80 tests** across all 4 services. All tests use mocks — no external dependencies needed.

---

## API Overview

### Auth Service (via `/api/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/auth/register` | Register a new user |
| POST | `/api/auth/auth/login` | Login (sets httpOnly cookies) |
| POST | `/api/auth/auth/logout` | Logout (clears cookies + revokes refresh token) |
| POST | `/api/auth/auth/refresh` | Refresh access token |
| POST | `/api/auth/auth/reset-password` | Reset password with token |
| GET | `/api/auth/user/profile` | Get current user profile |
| PUT | `/api/auth/user/profile` | Update profile (username, bio, avatar) |
| PUT | `/api/auth/user/change-password` | Change password |
| GET | `/api/auth/user/{username}` | Get any user's public profile |
| GET | `/api/auth/user/list` | List all users (admin only) |
| PUT | `/api/auth/user/role/{username}` | Change user role (admin only) |
| DELETE | `/api/auth/user/delete/{user_id}` | Soft-delete user (admin only) |

### Thread Service (via `/api/threads/`, `/api/search/`, `/api/tags/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/threads/feed` | Thread feed with pagination + filters |
| POST | `/api/threads/` | Create a thread |
| GET | `/api/threads/stats` | Thread + comment counts |
| GET | `/api/threads/user/{username}` | List threads by a specific user |
| GET | `/api/threads/{id}` | Get thread detail |
| PATCH | `/api/threads/{id}` | Edit thread (owner or admin) |
| DELETE | `/api/threads/{id}` | Delete thread (owner, moderator, or admin) |
| POST | `/api/threads/{id}/like` | Like/unlike a thread |
| GET | `/api/threads/{id}/comments` | List comments (nested tree) |
| POST | `/api/threads/{id}/comments` | Create a comment |
| PATCH | `/api/threads/comments/{id}` | Edit comment (owner or admin) |
| DELETE | `/api/threads/comments/{id}` | Delete comment (owner, moderator, or admin) |
| POST | `/api/threads/{id}/comments/{cid}/like` | Like/unlike a comment |
| GET | `/api/search/threads` | Full-text search |
| GET | `/api/search/users` | @mention autocomplete |
| GET | `/api/tags/` | List all tags |

### Notification Service (via `/api/notifications/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List notifications with pagination |
| GET | `/api/notifications/unread-count` | Get unread count |
| PATCH | `/api/notifications/{id}/read` | Mark one notification as read |
| PATCH | `/api/notifications/read-all` | Mark all as read |
| WS | `/ws/notifications` | Real-time notification stream |

---

## Documentation

Detailed documentation for every file and function:

| Document | Description |
|----------|-------------|
| [HLD.md](HLD.md) | High-Level Design — architecture, data flows, security model |
| [LLD.md](LLD.md) | Low-Level Design — line-by-line code explanations |
| [AUTH_SERVICE_DOCUMENTATION.md](Backend/services/auth-service/AUTH_SERVICE_DOCUMENTATION.md) | Auth service internals |
| [THREAD_SERVICE_DOCUMENTATION.md](Backend/services/thread-service/THREAD_SERVICE_DOCUMENTATION.md) | Thread service internals |
| [NOTIFICATION_SERVICE_DOCUMENTATION.md](Backend/services/notification-service/NOTIFICATION_SERVICE_DOCUMENTATION.md) | Notification service internals |
| [GATEWAY_DOCUMENTATION.md](Backend/gateway/GATEWAY_DOCUMENTATION.md) | Gateway proxy internals |

---

## Environment & Ports

| Service | Internal Port | Exposed Port | Database |
|---------|--------------|-------------|----------|
| Frontend | 5173 | 5173 | — |
| API Gateway | 8080 | 8080 | — |
| Auth Service | 8000 | 8000 | `threadix_auth` (5433) |
| Thread Service | 8001 | 8001 | `threadix_thread` (5434) |
| Notification Service | 8002 | 8002 | `threadix_notification` (5435) |
| Redis | 6379 | 6380 | — |
