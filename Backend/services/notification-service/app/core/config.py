from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = 'redis://localhost:6379'
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    ENVIRONMENT: str = 'development'

    class Config:
        env_file = '.env'


settings = Settings()
