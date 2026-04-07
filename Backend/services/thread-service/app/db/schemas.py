from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re
from app.utils.constants import MAX_TAG_LENGTH, TAG_REGEX


# ─── Tag schemas ─────────────────────────────────────────────────────────────
class TagOut(BaseModel):
    id: int
    name: str
    is_seeded: bool
    model_config = {'from_attributes': True}


class TagCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=MAX_TAG_LENGTH)

    @field_validator('name')
    def validate_tag_name(cls, v):
        v = v.lower().strip()
        if not re.match(TAG_REGEX, v):
            raise ValueError('Tag must be lowercase alphanumeric with hyphens, no spaces')
        return v


# ─── Author (embedded in thread/comment response) ────────────────────────────
class AuthorOut(BaseModel):
    id: int
    username: str
    avatar_url: Optional[str] = None
    model_config = {'from_attributes': True}


# ─── Thread schemas ───────────────────────────────────────────────────────────
class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=1)
    tag_ids: List[int] = Field(default=[], max_length=5)


class ThreadUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    tag_ids: Optional[List[int]] = Field(None, max_length=5)


class ThreadOut(BaseModel):
    id: int
    title: str
    description: str
    media_urls: List[str] = []
    like_count: int
    view_count: int
    comment_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    author: AuthorOut
    tags: List[TagOut] = []
    user_has_liked: bool = False   # injected at service layer
    model_config = {'from_attributes': True}


class ThreadListOut(BaseModel):
    threads: List[ThreadOut]
    total: int
    limit: int
    offset: int


# ─── Comment schemas ──────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: int
    thread_id: int
    parent_id: Optional[int]
    depth: int
    content: str
    like_count: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    author: Optional[AuthorOut] = None  # None if deleted
    child_count: int = 0               # injected: how many children exist
    model_config = {'from_attributes': True}


class CommentListOut(BaseModel):
    comments: List[CommentOut]
    total: int
    limit: int
    offset: int


# ─── Like schemas ─────────────────────────────────────────────────────────────
class LikeToggleIn(BaseModel):
    thread_id: Optional[int] = None
    comment_id: Optional[int] = None


class LikeToggleOut(BaseModel):
    liked: bool          # True = now liked, False = now unliked
    new_count: int


# ─── Notification schemas ─────────────────────────────────────────────────────
class NotificationOut(BaseModel):
    id: int
    type: str
    is_read: bool
    created_at: datetime
    thread_id: Optional[int]
    comment_id: Optional[int]
    actor: AuthorOut
    model_config = {'from_attributes': True}


# ─── Search schema ────────────────────────────────────────────────────────────
class SearchOut(BaseModel):
    threads: List[ThreadOut]
    total: int
