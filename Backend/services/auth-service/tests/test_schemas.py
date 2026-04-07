import pytest
from pydantic import ValidationError
from app.db.schemas import UserRegister, UserLogin, ChangePassword, UpdateProfile


def test_register_valid():
    u = UserRegister(email="test@example.com", password="secret123", username="alice")
    assert u.email == "test@example.com"
    assert u.username == "alice"


def test_register_short_password():
    with pytest.raises(ValidationError):
        UserRegister(email="test@example.com", password="abc", username="alice")


def test_register_short_username():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.com", password="secret123", username="ab")


def test_register_long_username():
    with pytest.raises(ValidationError):
        UserRegister(email="a@b.com", password="secret123", username="a" * 21)


def test_register_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(email="not-an-email", password="secret123", username="alice")


def test_login_valid():
    u = UserLogin(email="test@example.com", password="secret123")
    assert u.email == "test@example.com"


def test_change_password_valid():
    cp = ChangePassword(current_password="old123", new_password="new12345")
    assert cp.new_password == "new12345"


def test_change_password_short_new():
    with pytest.raises(ValidationError):
        ChangePassword(current_password="old123", new_password="abc")


def test_update_profile_optional_fields():
    p = UpdateProfile()
    assert p.username is None
    assert p.bio is None


def test_update_profile_bio_max_length():
    with pytest.raises(ValidationError):
        UpdateProfile(bio="x" * 301)
