from app.core.hashing import hash_password, verify_password


def test_hash_returns_string():
    h = hash_password("Secret123")
    assert isinstance(h, str)
    assert h != "Secret123"


def test_verify_correct_password():
    h = hash_password("Secret123")
    assert verify_password("Secret123", h) is True


def test_verify_wrong_password():
    h = hash_password("Secret123")
    assert verify_password("WrongPass", h) is False


def test_different_hashes_for_same_password():
    h1 = hash_password("Secret123")
    h2 = hash_password("Secret123")
    assert h1 != h2  # bcrypt uses random salt
