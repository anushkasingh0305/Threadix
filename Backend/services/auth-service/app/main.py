from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.utils.logger import logger
from app.api.routes import auth, user
import app.core.cloudinary_config  # noqa: F401

app = FastAPI(title="Threadix Auth Service")

# ✅ CORS configuration (required for cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(user.router, prefix="/user", tags=["User"])


async def _seed_admin():
    """Create the admin user on first boot if ADMIN_* env vars are set and no admin exists."""
    if not settings.ADMIN_EMAIL or not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        return
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.db.models import User, UserRole
    from app.core.hashing import hash_password
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.role == UserRole.admin).limit(1))
        if existing:
            logger.info(f"Admin seed skipped — admin already exists: {existing.username}")
            return
        admin = User(
            email=settings.ADMIN_EMAIL,
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.admin,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Admin seeded: {settings.ADMIN_USERNAME} ({settings.ADMIN_EMAIL})")


@app.on_event("startup")
async def startup():
    logger.info("Auth Service Started")
    await _seed_admin()

@app.get("/")
async def root():
    return {"message": "Threadix running"}