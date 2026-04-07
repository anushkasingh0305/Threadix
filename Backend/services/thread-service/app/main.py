from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import engine
from app.db.models import Base
from app.repositories.tag_repository import TagRepository
from app.db.database import get_db
from app.api.routes import threads, comments, likes, tags, search, notifications, websocket
from app.core.cloudinary_config import configure_cloudinary
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


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
    logger.info('Thread service started')
    yield
    # Shutdown
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
