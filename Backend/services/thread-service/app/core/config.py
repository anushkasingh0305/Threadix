from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = 'redis://localhost:6379'
    JWT_SECRET_KEY: str     # MUST match auth service secret
    JWT_ALGORITHM: str = 'HS256'
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    ENVIRONMENT: str = 'development'

    class Config:
        env_file = '.env'


settings = Settings()
