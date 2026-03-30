"""Tests for tools.py — SNS/community/SEO tool functions.

All API calls are mocked. Tests verify:
1. Missing env → proper error JSON
2. With env + mocked API → correct request flow + response parsing
3. CLI dispatch → correct function routing
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import tools


# ── Helpers ──────────────────────────────────────────────────


def _parse(result: str) -> dict:
    return json.loads(result)


def _mock_response(status_code=200, json_data=None, headers=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.text = text
    return resp


# ── ENV check tests (no credentials → error) ────────────────


class TestEnvCheck:
    """Every tool returns a clear error when required env vars are missing."""

    def setup_method(self):
        """Clear all SNS env vars before each test."""
        self._cleared = {}
        keys = [
            "INSTAGRAM_ACCOUNT_ID", "INSTAGRAM_ACCESS_TOKEN",
            "TIKTOK_ACCESS_TOKEN", "YOUTUBE_ACCESS_TOKEN",
            "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REFRESH_TOKEN",
            "DEVTO_API_KEY",
            "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "NAVER_BLOG_ACCESS_TOKEN",
            "RESEND_API_KEY",
            "TWITTER_BEARER_TOKEN",
            "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN",
        ]
        for k in keys:
            if k in os.environ:
                self._cleared[k] = os.environ.pop(k)

    def teardown_method(self):
        os.environ.update(self._cleared)

    def test_ig_reels_no_env(self):
        r = _parse(tools.ig_reels_upload("http://x.mp4", "caption"))
        assert "error" in r
        assert "INSTAGRAM" in r["error"]

    def test_tiktok_no_env(self):
        r = _parse(tools.tiktok_upload("http://x.mp4", "title"))
        assert "error" in r
        assert "TIKTOK" in r["error"]

    def test_yt_no_env(self):
        r = _parse(tools.yt_shorts_upload("video.mp4", "title"))
        assert "error" in r
        assert "YOUTUBE" in r["error"]

    def test_reddit_no_env(self):
        r = _parse(tools.reddit_comment("hello"))
        assert "error" in r
        assert "REDDIT" in r["error"]

    def test_devto_no_env(self):
        r = _parse(tools.devto_post("title", "body"))
        assert "error" in r
        assert "DEVTO" in r["error"]

    def test_naver_no_env(self):
        r = _parse(tools.naver_blog_post("title", "contents"))
        assert "error" in r
        assert "NAVER" in r["error"]

    def test_resend_no_env(self):
        r = _parse(tools.newsletter_send("subj", "<p>hi</p>", "a@b.com"))
        assert "error" in r
        assert "RESEND" in r["error"]

    def test_twitter_no_env(self):
        r = _parse(tools.twitter_post("hello"))
        assert "error" in r
        assert "TWITTER" in r["error"]

    def test_linkedin_no_env(self):
        r = _parse(tools.linkedin_post("hello"))
        assert "error" in r
        assert "LINKEDIN" in r["error"]

    def test_resend_no_recipients(self):
        with patch.dict(os.environ, {"RESEND_API_KEY": "fake"}):
            r = _parse(tools.newsletter_send("subj", "<p>hi</p>", ""))
            assert "error" in r
            assert "Recipient" in r["error"]


# ── Mocked API call tests ───────────────────────────────────


class TestDevtoPost:
    @patch("tools.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(201, {"id": 123, "url": "https://dev.to/test", "slug": "test"})
        with patch.dict(os.environ, {"DEVTO_API_KEY": "fake"}):
            r = _parse(tools.devto_post("Test Title", "# Hello", "python,ai"))
        assert r["id"] == 123
        assert "dev.to" in r["url"]
        call_args = mock_post.call_args
        body = call_args.kwargs["json"]["article"]
        assert body["title"] == "Test Title"
        assert body["tags"] == ["python", "ai"]
        assert body["published"] is False

    @patch("tools.httpx.post")
    def test_api_error(self, mock_post):
        mock_post.return_value = _mock_response(422, text="Validation failed")
        with patch.dict(os.environ, {"DEVTO_API_KEY": "fake"}):
            r = _parse(tools.devto_post("", ""))
        assert "error" in r
        assert "422" in r["error"]


class TestTwitterPost:
    @patch("tools.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(201, {"data": {"id": "999"}})
        with patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "fake"}):
            r = _parse(tools.twitter_post("Hello world"))
        assert r["tweet_id"] == "999"
        assert "999" in r["url"]

    @patch("tools.httpx.post")
    def test_with_reply(self, mock_post):
        mock_post.return_value = _mock_response(201, {"data": {"id": "1000"}})
        with patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "fake"}):
            tools.twitter_post("reply text", reply_to="888")
        body = mock_post.call_args.kwargs["json"]
        assert body["reply"]["in_reply_to_tweet_id"] == "888"


class TestLinkedinPost:
    @patch("tools.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(201, {"id": "urn:li:share:123"}, headers={"X-RestLi-Id": "urn:li:share:123"})
        with patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "fake", "LINKEDIN_AUTHOR_URN": "urn:li:person:abc"}):
            r = _parse(tools.linkedin_post("Hello LinkedIn"))
        assert r["post_id"] == "urn:li:share:123"
        assert r["status"] == "PUBLISHED"


class TestNewsletterSend:
    @patch("tools.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(200, {"id": "email-123"})
        with patch.dict(os.environ, {"RESEND_API_KEY": "fake"}):
            r = _parse(tools.newsletter_send("Weekly", "<h1>Hi</h1>", "user@example.com"))
        assert r["id"] == "email-123"
        assert r["status"] == "sent"
        body = mock_post.call_args.kwargs["json"]
        assert body["to"] == ["user@example.com"]

    @patch("tools.httpx.post")
    def test_multiple_recipients(self, mock_post):
        mock_post.return_value = _mock_response(200, {"id": "email-456"})
        with patch.dict(os.environ, {"RESEND_API_KEY": "fake"}):
            r = _parse(tools.newsletter_send("News", "<p>hi</p>", "a@b.com,c@d.com"))
        body = mock_post.call_args.kwargs["json"]
        assert body["to"] == ["a@b.com", "c@d.com"]


class TestNaverBlogPost:
    @patch("tools.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response(200, {"log_no": "222", "url": "https://blog.naver.com/test/222"})
        env = {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret", "NAVER_BLOG_ACCESS_TOKEN": "tok"}
        with patch.dict(os.environ, env):
            r = _parse(tools.naver_blog_post("Test Title", "<p>Content</p>"))
        assert r["log_no"] == "222"


class TestRedditComment:
    @patch("tools.httpx.post")
    def test_comment_success(self, mock_post):
        # First call = auth, second = comment
        mock_post.side_effect = [
            _mock_response(200, {"access_token": "tok123"}),
            _mock_response(200, {"json": {"data": {"things": [{"data": {"id": "t1_abc"}}]}}}),
        ]
        env = {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "sec", "REDDIT_REFRESH_TOKEN": "ref"}
        with patch.dict(os.environ, env):
            r = _parse(tools.reddit_comment("great post!", parent_id="t3_xyz"))
        assert mock_post.call_count == 2

    @patch("tools.httpx.post")
    def test_comment_without_parent_id(self, mock_post):
        mock_post.return_value = _mock_response(200, {"access_token": "tok"})
        env = {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "sec", "REDDIT_REFRESH_TOKEN": "ref"}
        with patch.dict(os.environ, env):
            r = _parse(tools.reddit_comment("text", kind="comment"))
        assert "error" in r
        assert "parent_id" in r["error"]


class TestTiktokUpload:
    @patch("tools.time.sleep")  # skip actual waiting
    @patch("tools.httpx.post")
    def test_success(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            _mock_response(200, {"data": {"publish_id": "pub123"}}),  # init
            _mock_response(200, {"data": {"status": "PUBLISH_COMPLETE"}}),  # poll
        ]
        with patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "fake"}):
            r = _parse(tools.tiktok_upload("https://cdn.example.com/v.mp4", "My Video"))
        assert r["publish_id"] == "pub123"
        assert r["status"] == "PUBLISH_COMPLETE"

    @patch("tools.httpx.post")
    def test_init_fail(self, mock_post):
        mock_post.return_value = _mock_response(400, text="Bad request")
        with patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "fake"}):
            r = _parse(tools.tiktok_upload("bad", "title"))
        assert "error" in r
        assert "400" in r["error"]


class TestIgReelsUpload:
    @patch("tools.time.sleep")
    @patch("tools.httpx.get")
    @patch("tools.httpx.post")
    def test_full_flow(self, mock_post, mock_get, mock_sleep):
        # create container → poll FINISHED → publish
        mock_post.side_effect = [
            _mock_response(200, {"id": "container_1"}),  # create
            _mock_response(200, {"id": "post_1"}),        # publish
        ]
        mock_get.return_value = _mock_response(200, {"status_code": "FINISHED"})
        env = {"INSTAGRAM_ACCOUNT_ID": "123", "INSTAGRAM_ACCESS_TOKEN": "tok"}
        with patch.dict(os.environ, env):
            r = _parse(tools.ig_reels_upload("https://cdn.example.com/v.mp4", "#saju"))
        assert r["post_id"] == "post_1"
        assert r["status"] == "PUBLISHED"

    @patch("tools.httpx.post")
    def test_container_creation_fail(self, mock_post):
        mock_post.return_value = _mock_response(400, text="Invalid video URL")
        env = {"INSTAGRAM_ACCOUNT_ID": "123", "INSTAGRAM_ACCESS_TOKEN": "tok"}
        with patch.dict(os.environ, env):
            r = _parse(tools.ig_reels_upload("bad", "caption"))
        assert "error" in r
        assert "400" in r["error"]


class TestYtShortsUpload:
    @patch("tools.httpx.put")
    @patch("tools.httpx.post")
    def test_success(self, mock_post, mock_put):
        mock_post.return_value = _mock_response(200, headers={"Location": "https://upload.youtube.com/xxx"})
        mock_put.return_value = _mock_response(200, {"id": "vid123", "status": {"uploadStatus": "uploaded"}})
        tmp_file = Path("tests/_test_video.mp4")
        tmp_file.write_bytes(b"\x00" * 100)
        try:
            with patch.dict(os.environ, {"YOUTUBE_ACCESS_TOKEN": "fake"}):
                r = _parse(tools.yt_shorts_upload(str(tmp_file), "Test Short"))
            assert r["video_id"] == "vid123"
            assert "shorts" in r["url"]
        finally:
            tmp_file.unlink(missing_ok=True)

    def test_file_not_found(self):
        with patch.dict(os.environ, {"YOUTUBE_ACCESS_TOKEN": "fake"}):
            with patch("tools.httpx.post", return_value=_mock_response(200, headers={"Location": "https://x"})):
                r = _parse(tools.yt_shorts_upload("/nonexistent.mp4", "title"))
        assert "error" in r
        assert "not found" in r["error"]


# ── Directory submit (file logging) ─────────────────────────


class TestDirectorySubmit:
    def test_creates_log_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tools, "BASE_DIR", tmp_path)
        r = _parse(tools.directory_submit("ProductHunt", "MyApp", "https://myapp.com", "AI tool"))
        assert r["status"] == "pending"
        assert r["directory"] == "ProductHunt"
        log_file = tmp_path / "output" / "directory-submissions" / "producthunt.json"
        assert log_file.exists()
        saved = json.loads(log_file.read_text(encoding="utf-8"))
        assert saved["product"] == "MyApp"


# ── Existing tools still work ────────────────────────────────


class TestExistingTools:
    def test_web_search_no_key(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BRAVE_SEARCH_API_KEY", None)
            r = _parse(tools.web_search("test"))
            assert "error" in r

    def test_list_projects(self):
        r = json.loads(tools.list_projects())
        assert isinstance(r, list)
        slugs = [p["slug"] for p in r]
        assert "saju" in slugs

    @patch("tools.httpx.get")
    def test_check_meta(self, mock_get):
        mock_get.return_value = _mock_response(200, text="<html><title>Test</title></html>")
        r = _parse(tools.check_meta("https://example.com"))
        assert r["title"]["text"] == "Test"

    def test_check_meta_invalid_url(self):
        r = _parse(tools.check_meta("ftp://bad"))
        assert "error" in r
