from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ActorOut(BaseModel):
    id: int
    username: str
    avatar_url: Optional[str] = None
    model_config = {'from_attributes': True}


class NotificationOut(BaseModel):
    id: int
    type: str
    is_read: bool
    thread_id: Optional[int]
    comment_id: Optional[int]
    created_at: datetime
    actor_id: int
    model_config = {'from_attributes': True}


class NotificationListOut(BaseModel):
    notifications: list[NotificationOut]
    total: int
    unread_count: int
    limit: int
    offset: int
