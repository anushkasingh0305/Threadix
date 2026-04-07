from fastapi import Request, HTTPException
from app.core.security import decode_token


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id


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