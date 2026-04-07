import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db.models import Base
from app.services.consumer import start_consumer
from app.api.routes import notifications, websocket
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start the Redis event consumer as a background task.
    consumer_task = asyncio.create_task(start_consumer())
    logger.info('Notification service started. Consumer running.')

    yield  # server runs here

    # Graceful shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info('Notification service stopped.')


app = FastAPI(title='Threadix Notification Service', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://localhost:8002',
        'http://localhost',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(notifications.router)
app.include_router(websocket.router)


@app.get('/')
async def root():
    return {'service': 'threadix-notification-service', 'status': 'ok'}
