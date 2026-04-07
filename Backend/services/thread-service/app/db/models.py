import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, Enum, ARRAY, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# ─── Enums ───────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin     = 'admin'
    moderator = 'moderator'
    member    = 'member'

class NotificationType(str, enum.Enum):
    reply   = 'reply'
    mention = 'mention'
    like    = 'like'
    comment = 'comment'

# ─── UserCache ───────────────────────────────────────────────────────────────
class UserCache(Base):
    __tablename__ = 'users_cache'
    id         = Column(Integer, primary_key=True)   # matches auth user.id
    username   = Column(String(50), unique=True, nullable=False, index=True)
    avatar_url = Column(String, nullable=True)
    role       = Column(Enum(UserRole), default=UserRole.member)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ─── Tag ─────────────────────────────────────────────────────────────────────
class Tag(Base):
    __tablename__ = 'tags'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(30), unique=True, nullable=False, index=True)
    is_seeded  = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('users_cache.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ─── ThreadTag (join) ─────────────────────────────────────────────────────────
class ThreadTag(Base):
    __tablename__ = 'thread_tags'
    thread_id  = Column(Integer, ForeignKey('threads.id', ondelete='CASCADE'), primary_key=True)
    tag_id     = Column(Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)

# ─── Thread ───────────────────────────────────────────────────────────────────
class Thread(Base):
    __tablename__ = 'threads'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey('users_cache.id'), nullable=False, index=True)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=False)
    media_urls    = Column(ARRAY(String), default=[])
    like_count    = Column(Integer, default=0, nullable=False)
    view_count    = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    is_deleted    = Column(Boolean, default=False, index=True)
    created_at    = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    tags     = relationship('Tag', secondary='thread_tags', lazy='selectin')
    author   = relationship('UserCache', foreign_keys=[user_id], lazy='selectin')
    comments = relationship('Comment', back_populates='thread', cascade='all,delete-orphan')

# ─── Comment ─────────────────────────────────────────────────────────────────
class Comment(Base):
    __tablename__ = 'comments'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    thread_id  = Column(Integer, ForeignKey('threads.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey('users_cache.id'), nullable=False)
    parent_id  = Column(Integer, ForeignKey('comments.id', ondelete='SET NULL'), nullable=True, index=True)
    depth      = Column(Integer, default=0, nullable=False)
    content    = Column(Text, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    thread   = relationship('Thread', back_populates='comments')
    author   = relationship('UserCache', foreign_keys=[user_id], lazy='selectin')
    children = relationship('Comment', foreign_keys=[parent_id],
                            lazy='dynamic', back_populates='parent')
    parent   = relationship('Comment', foreign_keys=[parent_id],
                            remote_side='Comment.id', back_populates='children')

# ─── Like ────────────────────────────────────────────────────────────────────
class Like(Base):
    __tablename__ = 'likes'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey('users_cache.id'), nullable=False)
    thread_id  = Column(Integer, ForeignKey('threads.id',  ondelete='CASCADE'), nullable=True)
    comment_id = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('user_id', 'thread_id',  name='uq_like_user_thread'),
        UniqueConstraint('user_id', 'comment_id', name='uq_like_user_comment'),
    )

# ─── Notification ─────────────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = 'notifications'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(Integer, ForeignKey('users_cache.id'), nullable=False, index=True)
    actor_id     = Column(Integer, ForeignKey('users_cache.id'), nullable=False)
    type         = Column(Enum(NotificationType), nullable=False)
    thread_id    = Column(Integer, ForeignKey('threads.id',  ondelete='CASCADE'), nullable=True)
    comment_id   = Column(Integer, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    # Relationships
    actor        = relationship('UserCache', foreign_keys=[actor_id], lazy='selectin')

# ─── UserTagAffinity ─────────────────────────────────────────────────────────
class UserTagAffinity(Base):
    __tablename__ = 'user_tag_affinity'
    user_id    = Column(Integer, ForeignKey('users_cache.id'), primary_key=True)
    tag_id     = Column(Integer, ForeignKey('tags.id'), primary_key=True)
    score      = Column(Float, default=0.0, nullable=False)
    __table_args__ = (
        Index('idx_uta_user_id', 'user_id'),
    )
