"""Tests for Xueqiu collector (mocked HTTP)."""

from unittest.mock import MagicMock, patch

import pytest

from collectors.xueqiu import XueqiuCollector, _strip_html, _ms_to_datetime


def test_strip_html():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert _strip_html("No tags here") == "No tags here"
    assert _strip_html("&amp; &lt; &gt;") == "& < >"


def test_ms_to_datetime():
    dt = _ms_to_datetime(1700000000000)
    assert dt is not None
    assert dt.year >= 2023


def test_ms_to_datetime_none():
    assert _ms_to_datetime(None) is None
    assert _ms_to_datetime(0) is None


@pytest.fixture
def mock_timeline_response():
    return {
        "list": [
            {
                "id": 12345,
                "user": {"id": 111, "screen_name": "TestUser"},
                "title": "A股大涨",
                "text": "<p>今天<b>沪深300</b>指数上涨3%</p>",
                "reply_count": 42,
                "created_at": 1700000000000,
            },
            {
                "id": 12346,
                "user": {"id": 222, "screen_name": "Analyst"},
                "title": "",
                "text": "Bitcoin is trending today with massive volume",
                "reply_count": 10,
                "created_at": 1700001000000,
            },
        ]
    }


@patch("collectors.xueqiu.XUEQIU_COOKIE", "test_cookie")
@patch("collectors.xueqiu.XUEQIU_KOL_IDS", [])
def test_collect_timeline(mock_timeline_response):
    with patch("requests.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_timeline_response
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        collector = XueqiuCollector()
        collector._session = mock_session
        articles = collector.collect()

        assert len(articles) == 4  # 2 articles x 2 categories (hot, stocks)
        first = articles[0]
        assert first["source"] == "xueqiu"
        assert first["source_id"] == "xueqiu_12345"
        assert first["author"] == "TestUser"
        assert "沪深300" in first["content"]
        assert "<b>" not in first["content"]  # HTML stripped
        assert first["score"] == 42


@patch("collectors.xueqiu.XUEQIU_COOKIE", "test_cookie")
@patch("collectors.xueqiu.XUEQIU_KOL_IDS", [])
def test_dedup_source_id():
    """Verify source_id format for dedup."""
    with patch("requests.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"list": [
            {"id": 99, "user": {"id": 1, "screen_name": "A"}, "text": "test content", "reply_count": 0}
        ]}
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        collector = XueqiuCollector()
        collector._session = mock_session
        articles = collector.collect()

        for a in articles:
            assert a["source_id"].startswith("xueqiu_")
