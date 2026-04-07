import re
import pytest

from app.services.consumer import CHANNEL_RE


def test_channel_regex_matches_valid():
    m = CHANNEL_RE.match("user:42:notifs")
    assert m is not None
    assert m.group(1) == "42"


def test_channel_regex_matches_large_id():
    m = CHANNEL_RE.match("user:123456:notifs")
    assert m is not None
    assert m.group(1) == "123456"


def test_channel_regex_no_match_wrong_format():
    assert CHANNEL_RE.match("thread:1:comments") is None


def test_channel_regex_no_match_missing_id():
    assert CHANNEL_RE.match("user::notifs") is None
