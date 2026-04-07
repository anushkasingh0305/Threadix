from jose import JWTError, jwt
from app.core.config import settings


def decode_token(token: str) -> dict:
    """
    Decodes JWT and returns payload dict.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
