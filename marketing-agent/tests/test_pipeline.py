"""Tests for /api/pipeline/trigger endpoint."""

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from marketing_agent.routes import create_app

client = TestClient(create_app())


@pytest.fixture()
def fake_pages(tmp_path):
    """Create fake PNG files in a temp dir."""
    for i in range(1, 6):
        (tmp_path / f"page_{i}.png").write_bytes(b"\x89PNG_FAKE_" + bytes([i]) * 50)
    return tmp_path


class TestPipelineTriggerDryRun:
    """dry_run=true skips n8n call, returns content + images."""

    def test_dry_run_returns_content(self, fake_pages):
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            r = client.post("/api/pipeline/trigger", json={"project": "saju", "dry_run": True})
        assert r.status_code == 200
        data = r.json()
        assert data["image_count"] == 5
        assert data["narrative_count"] >= 5
        assert data["dry_run"] is True
        assert data["n8n_status"] is None
        assert "title" in data
        assert "hashtags" in data

    def test_dry_run_with_template(self, fake_pages):
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            r = client.post("/api/pipeline/trigger", json={
                "project": "saju", "template": "금전운 특집", "dry_run": True,
            })
        assert r.status_code == 200
        assert r.json()["image_count"] == 5

    def test_missing_pages_dir(self, tmp_path):
        missing = tmp_path / "nonexistent"
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", missing):
            r = client.post("/api/pipeline/trigger", json={"project": "saju", "dry_run": True})
        assert r.status_code == 404
        assert "not found" in r.json()["detail"]

    def test_empty_pages_dir(self, tmp_path):
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", tmp_path):
            r = client.post("/api/pipeline/trigger", json={"project": "saju", "dry_run": True})
        assert r.status_code == 404
        assert "No page_*.png" in r.json()["detail"]


class TestPipelineN8nIntegration:
    """dry_run=false triggers n8n webhook."""

    @patch("marketing_agent.routes.pipeline.httpx.post")
    def test_n8n_webhook_called(self, mock_post, fake_pages):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"executionId": "abc123"}'
        mock_post.return_value = mock_resp

        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            r = client.post("/api/pipeline/trigger", json={"project": "saju", "dry_run": False})

        assert r.status_code == 200
        data = r.json()
        assert data["n8n_status"] == 200
        assert "abc123" in data["n8n_response"]
        assert data["dry_run"] is False

        # Verify webhook payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert "images" in payload
        assert "narrativeTexts" in payload
        assert "title" in payload
        assert "config" in payload
        assert len(payload["images"]) == 5
        assert len(payload["narrativeTexts"]) >= 5
        # Each image has correct shape
        img = payload["images"][0]
        assert "imageBase64" in img
        assert "prompt" in img
        assert img["mimeType"] == "image/png"
        # Verify base64 is valid
        base64.b64decode(img["imageBase64"])
        # Config has correct voice
        assert payload["config"]["voice"] == "21m00Tcm4TlvDq8ikWAM"

    @patch("marketing_agent.routes.pipeline.httpx.post")
    def test_n8n_webhook_failure(self, mock_post, fake_pages):
        mock_post.side_effect = Exception("Connection refused")

        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            r = client.post("/api/pipeline/trigger", json={"project": "saju"})

        assert r.status_code == 200  # endpoint succeeds even if n8n fails
        data = r.json()
        assert data["n8n_status"] == 0
        assert "Connection refused" in data["n8n_response"]


class TestLoadPageImages:
    """Test _load_page_images helper."""

    def test_loads_sorted(self, fake_pages):
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            from marketing_agent.routes.pipeline import _load_page_images
            images = _load_page_images()
        assert len(images) == 5
        assert images[0]["prompt"].endswith("1")
        assert images[4]["prompt"].endswith("5")

    def test_base64_roundtrip(self, fake_pages):
        with patch("marketing_agent.routes.pipeline.LM_PAGES_DIR", fake_pages):
            from marketing_agent.routes.pipeline import _load_page_images
            images = _load_page_images()
        original = (fake_pages / "page_1.png").read_bytes()
        decoded = base64.b64decode(images[0]["imageBase64"])
        assert decoded == original
