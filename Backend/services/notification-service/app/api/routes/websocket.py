import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie
from jose import JWTError
from app.core.security import decode_token
from app.db.redis import subscribe, set_user_online, set_user_offline

router = APIRouter()


async def _forward(ws: WebSocket, pubsub):
    """Forward Redis messages to the WebSocket client."""
    try:
        async for msg in pubsub.listen():
            if msg['type'] == 'message':
                await ws.send_text(msg['data'])
    except Exception:
        pass


async def _heartbeat(ws: WebSocket, user_id: int):
    """Every 20 seconds, renew the online TTL and send ping."""
    try:
        while True:
            await asyncio.sleep(20)
            await set_user_online(user_id)
            await ws.send_text(json.dumps({'type': 'ping'}))
    except Exception:
        pass


@router.websocket('/ws/notifications')
async def notification_ws(
    ws: WebSocket,
    access_token: str = Cookie(default=None),
):
    if not access_token:
        await ws.close(code=4001)
        return
    try:
        payload = decode_token(access_token)
        user_id = int(payload['sub'])
    except JWTError:
        await ws.close(code=4001)
        return

    await ws.accept()
    await set_user_online(user_id)

    pubsub = await subscribe(f'user:{user_id}:ws')

    forward_task   = asyncio.create_task(_forward(ws, pubsub))
    heartbeat_task = asyncio.create_task(_heartbeat(ws, user_id))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get('type') == 'pong':
                await set_user_online(user_id)
    except WebSocketDisconnect:
        forward_task.cancel()
        heartbeat_task.cancel()
        await pubsub.unsubscribe()
        await set_user_offline(user_id)
