import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, Index
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserRole(str, enum.Enum):
    admin     = 'admin'
    moderator = 'moderator'
    member    = 'member'


class NotificationType(str, enum.Enum):
    reply   = 'reply'
    mention = 'mention'
    like    = 'like'
    comment = 'comment'


class UserCache(Base):
    __tablename__ = 'users_cache'
    id         = Column(Integer, primary_key=True)
    username   = Column(String(50), unique=True, nullable=False)
    email      = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    role       = Column(Enum(UserRole), default=UserRole.member)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    __tablename__ = 'notifications'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    recipient_id = Column(Integer, nullable=False)
    actor_id     = Column(Integer, nullable=False)
    type         = Column(Enum(NotificationType), nullable=False)
    thread_id    = Column(Integer, nullable=True)
    comment_id   = Column(Integer, nullable=True)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index('idx_notif_recipient_created', 'recipient_id', 'created_at'),
    )
