from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.schemas import UserRegister, UserLogin
from app.services.auth_service import register_user, login_user, refresh_tokens, logout_user
from app.services.password_services import reset_password
from app.core.security import decode_token

router = APIRouter()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register")
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        await register_user(db, user)
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login")
async def login(user: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        access, refresh = await login_user(db, user)

        response.set_cookie("access_token", access, httponly=True)
        response.set_cookie("refresh_token", refresh, httponly=True)

        return {"message": "Login successful"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    access, new_refresh = await refresh_tokens(token, db=db)

    response = JSONResponse({"message": "Refreshed"})
    response.set_cookie("access_token", access, httponly=True)
    response.set_cookie("refresh_token", new_refresh, httponly=True)

    return response


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="No access token")

    try:
        payload = decode_token(token)
        await logout_user(payload["sub"])
    except Exception:
        pass  # still clear cookies even if token is expired

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"message": "Logged out"}


@router.post("/reset-password")
async def do_reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        await reset_password(db, body.token, body.new_password)
        return {"message": "Password reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))