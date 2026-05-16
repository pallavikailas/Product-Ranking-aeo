"""Unit tests for scripts/badge_status.py — no network calls made."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.badge_status import get_app_status, get_badge_url


# ── get_app_status ─────────────────────────────────────────────────────────────

def test_get_app_status_online_for_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("scripts.badge_status.requests.get", return_value=mock_resp):
        assert get_app_status("https://example.com") == "online"


def test_get_app_status_offline_for_connection_error():
    with patch(
        "scripts.badge_status.requests.get",
        side_effect=requests.exceptions.ConnectionError(),
    ):
        assert get_app_status("https://example.com") == "offline"


def test_get_app_status_offline_for_5xx():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("scripts.badge_status.requests.get", return_value=mock_resp):
        assert get_app_status("https://example.com") == "offline"


def test_get_app_status_unknown_for_timeout():
    with patch(
        "scripts.badge_status.requests.get",
        side_effect=requests.exceptions.Timeout(),
    ):
        assert get_app_status("https://example.com") == "unknown"


# ── get_badge_url ──────────────────────────────────────────────────────────────

def test_get_badge_url_online_contains_green():
    url = get_badge_url("online")
    assert "shields.io" in url
    assert "green" in url


def test_get_badge_url_offline_contains_red():
    url = get_badge_url("offline")
    assert "shields.io" in url
    assert "red" in url


def test_get_badge_url_unknown_contains_grey():
    url = get_badge_url("unknown")
    assert "shields.io" in url
    assert "grey" in url


def test_get_badge_url_format():
    for status in ("online", "offline", "unknown"):
        url = get_badge_url(status)
        assert url.startswith("https://img.shields.io/badge/")
