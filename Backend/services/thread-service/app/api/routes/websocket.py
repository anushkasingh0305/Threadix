import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.db.redis import subscribe_to_channel

router = APIRouter()


async def _forward_messages(ws: WebSocket, pubsub):
    """Listen to Redis pub/sub and forward messages to WS client."""
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await ws.send_text(message['data'])
    except Exception:
        pass  # client disconnected


@router.websocket('/ws')
async def websocket_endpoint(
    ws: WebSocket,
    channels: str = Query(..., description='Comma-separated channel names'),
):
    """
    Client connects as: ws://host/ws?channels=threads,thread:5:likes,user:3:notifs
    Each channel maps to a Redis pub/sub channel.
    """
    await ws.accept()
    channel_list = [c.strip() for c in channels.split(',') if c.strip()]

    # Subscribe to all requested channels
    pubsub_objects = []
    for channel in channel_list:
        ps = await subscribe_to_channel(channel)
        pubsub_objects.append(ps)

    # Start forwarding tasks for all pubsub listeners
    tasks = [
        asyncio.create_task(_forward_messages(ws, ps))
        for ps in pubsub_objects
    ]

    try:
        while True:
            # Keep alive — wait for client disconnect
            await ws.receive_text()
    except WebSocketDisconnect:
        for task in tasks:
            task.cancel()
        for ps in pubsub_objects:
            await ps.unsubscribe()
