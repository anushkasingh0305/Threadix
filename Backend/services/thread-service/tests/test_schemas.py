import os
import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")

from app.db.schemas import ThreadCreate, ThreadUpdate, CommentCreate, CommentUpdate


def test_thread_create_valid():
    t = ThreadCreate(title="My Thread", description="Hello world")
    assert t.title == "My Thread"
    assert t.tag_ids == []


def test_thread_create_short_title():
    with pytest.raises(ValidationError):
        ThreadCreate(title="ab", description="text")


def test_thread_create_long_title():
    with pytest.raises(ValidationError):
        ThreadCreate(title="x" * 201, description="text")


def test_thread_create_empty_description():
    with pytest.raises(ValidationError):
        ThreadCreate(title="valid", description="")


def test_thread_create_too_many_tags():
    with pytest.raises(ValidationError):
        ThreadCreate(title="valid", description="text", tag_ids=[1, 2, 3, 4, 5, 6])


def test_thread_update_optional():
    t = ThreadUpdate()
    assert t.title is None
    assert t.description is None
    assert t.tag_ids is None


def test_thread_update_short_title():
    with pytest.raises(ValidationError):
        ThreadUpdate(title="ab")


def test_comment_create_valid():
    c = CommentCreate(content="Nice post!")
    assert c.content == "Nice post!"
    assert c.parent_id is None


def test_comment_update_valid():
    c = CommentUpdate(content="Edited comment")
    assert c.content == "Edited comment"
