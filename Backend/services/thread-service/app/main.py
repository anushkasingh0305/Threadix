import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import update as sa_update
from app.db.database import engine, AsyncSessionLocal
from app.db.models import Base, UserCache
from app.repositories.tag_repository import TagRepository
from app.db.database import get_db
from app.api.routes import threads, comments, likes, tags, search, notifications, websocket
from app.core.cloudinary_config import configure_cloudinary
from app.db.redis import consume_profile_updates
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def _profile_sync_worker():
    """Background worker: consumes Redis stream and updates users_cache."""
    last_id = '0-0'  # process all existing messages first, then new ones
    while True:
        try:
            messages = await consume_profile_updates(last_id)
            if not messages:
                continue
            for msg_id, fields in messages:
                user_id = int(fields['user_id'])
                username = fields['username']
                avatar_url = fields['avatar_url'] or None

                async with AsyncSessionLocal() as db:
                    await db.execute(
                        sa_update(UserCache)
                        .where(UserCache.id == user_id)
                        .values(username=username, avatar_url=avatar_url)
                    )
                    await db.commit()

                last_id = msg_id
                logger.info(f'Synced profile for user {user_id} ({username})')
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f'Profile sync error: {e}')
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_cloudinary()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed tags
    async for db in get_db():
        await TagRepository.seed(db)
        break
    # Start profile-sync background worker
    sync_task = asyncio.create_task(_profile_sync_worker())
    logger.info('Thread service started')
    yield
    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info('Thread service stopped')


app = FastAPI(title='Threadix Thread Service', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://localhost:8000',
        'http://localhost:8001',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(threads.router)
app.include_router(comments.router)
app.include_router(likes.router)
app.include_router(tags.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(websocket.router)


@app.get('/')
async def root():
    return {'service': 'threadix-thread-service', 'status': 'ok'}
