"""Pipeline API — /api/pipeline/*

Bridges ARG content generation with n8n webhook format.
ARG produces: {title, hashtags, scenes[], config}
n8n expects:  {title, hashtags, images[{imageBase64, prompt, mimeType}], narrativeTexts[], config}

This endpoint:
1. Generates content via ContentGenerator
2. Reads LM/pages/page_*.png → base64
3. Maps scenes[].text → narrativeTexts[]
4. Optionally POSTs to n8n webhook
"""

import base64
import logging
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import BASE_DIR
from ..generator import ContentGenerator
from ..models import ContentRequest

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Default paths — configurable via env
LM_PAGES_DIR = Path(os.environ.get(
    "LM_PAGES_DIR",
    str(BASE_DIR.parent.parent / "LM" / "pages"),
))
N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    "https://cgxr.app.n8n.cloud/webhook/saju-daily",
)
# Voice ID for ElevenLabs (Railway/n8n default)
ELEVENLABS_VOICE = "21m00Tcm4TlvDq8ikWAM"


class PipelineRequest(BaseModel):
    project: str = "saju"
    mode: str = "template"
    template: str | None = None
    date: str | None = None
    dry_run: bool = False  # True = skip n8n webhook POST


class PipelineResponse(BaseModel):
    title: str
    hashtags: str
    image_count: int
    narrative_count: int
    category: str = "unknown"
    dry_run: bool = False
    n8n_status: int | None = None
    n8n_response: str | None = None


def _load_page_images() -> list[dict]:
    """Read LM/pages/page_*.png and return base64-encoded image dicts."""
    images = []
    if not LM_PAGES_DIR.is_dir():
        raise FileNotFoundError(f"LM pages directory not found: {LM_PAGES_DIR}")
    for png in sorted(LM_PAGES_DIR.glob("page_*.png")):
        raw = png.read_bytes()
        images.append({
            "imageBase64": base64.b64encode(raw).decode("ascii"),
            "prompt": f"사주 운세 페이지 {png.stem.split('_')[-1]}",
            "mimeType": "image/png",
        })
    if not images:
        raise FileNotFoundError(f"No page_*.png files in {LM_PAGES_DIR}")
    return images


@router.post("/trigger", response_model=PipelineResponse)
async def trigger_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Generate content + transform to n8n format + optionally trigger webhook."""

    # 1. Generate content
    content_req = ContentRequest(
        project=request.project,
        mode=request.mode,
        template=request.template,
        date=request.date,
    )
    gen = ContentGenerator(project_slug=request.project)
    content = gen.create(content_req)

    # 2. Load PNG images
    try:
        images = _load_page_images()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 3. Map scenes → narrativeTexts
    narrative_texts = [scene.text for scene in content.scenes]

    # 4. Build n8n-compatible payload
    payload = {
        "title": content.title,
        "hashtags": content.hashtags,
        "images": images,
        "narrativeTexts": narrative_texts,
        "config": {
            "orientation": "portrait",
            "voice": ELEVENLABS_VOICE,
            "musicVolume": "low",
            "subtitlePosition": "bottom",
        },
    }

    # 5. POST to n8n webhook (unless dry_run)
    n8n_status = None
    n8n_response = None
    if not request.dry_run:
        try:
            resp = httpx.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
            n8n_status = resp.status_code
            n8n_response = resp.text[:500]
        except Exception as e:
            log.error("n8n webhook failed: %s", e)
            n8n_status = 0
            n8n_response = str(e)

    return PipelineResponse(
        title=content.title,
        hashtags=content.hashtags,
        image_count=len(images),
        narrative_count=len(narrative_texts),
        category=content.category,
        dry_run=request.dry_run,
        n8n_status=n8n_status,
        n8n_response=n8n_response,
    )
