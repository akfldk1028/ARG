"""Marketing Agent A2A Server — port 9020

Unified marketing + SEO team capabilities via Google A2A protocol.
Agent card at GET /.well-known/agent.json
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Marketing Agent A2A", version="1.0.0")

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = (BASE_DIR / "output").resolve()


def _load_all_projects() -> list[dict]:
    """Load all project configs."""
    projects_dir = BASE_DIR / "projects"
    projects = []
    if projects_dir.is_dir():
        for f in sorted(projects_dir.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                data["_slug"] = f.stem
                projects.append(data)
    if not projects:
        root = BASE_DIR / "project.yaml"
        if root.exists():
            with open(root, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                data["_slug"] = "default"
                projects.append(data)
    return projects


def _safe_output_path(*parts: str) -> Path:
    """Resolve output path and verify it stays within OUTPUT_DIR."""
    resolved = (OUTPUT_DIR / Path(*parts)).resolve()
    if not str(resolved).startswith(str(OUTPUT_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    return resolved


# --- A2A Agent Card ---

ALL_AGENTS = [
    "cmo", "content-writer", "social-media-manager", "performance-analyst",
    "keyword-researcher", "content-optimizer", "competitor-analyst",
]

AGENT_CARD = {
    "name": "Marketing Agent Team",
    "description": "AI-powered marketing + SEO team: 7 agents for content, social, SEO, and analytics",
    "url": "http://localhost:9020",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        # Marketing skills
        {
            "id": "create-content",
            "name": "Create Content",
            "description": "Generate blog posts, articles, and marketing copy",
        },
        {
            "id": "create-social-posts",
            "name": "Create Social Posts",
            "description": "Generate platform-specific social media posts",
        },
        {
            "id": "performance-report",
            "name": "Performance Report",
            "description": "Generate marketing performance analysis report",
        },
        {
            "id": "weekly-plan",
            "name": "Weekly Plan",
            "description": "Create weekly marketing strategy and content calendar",
        },
        # SEO skills
        {
            "id": "keyword-research",
            "name": "Keyword Research",
            "description": "Discover keywords, analyze search intent, estimate difficulty",
        },
        {
            "id": "content-audit",
            "name": "Content Audit",
            "description": "Audit content for on-page SEO, meta tags, structured data",
        },
        {
            "id": "competitor-analysis",
            "name": "Competitor Analysis",
            "description": "Analyze competitor content strategies and identify gaps",
        },
        {
            "id": "content-brief",
            "name": "Content Brief",
            "description": "Generate SEO-optimized content briefs for writers",
        },
    ],
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
}


@app.get("/.well-known/agent.json")
async def agent_card():
    """Return A2A agent card."""
    return JSONResponse(content=AGENT_CARD)


@app.get("/health")
async def health():
    """Health check with active projects."""
    projects = _load_all_projects()
    return {
        "status": True,
        "service": "marketing-agent",
        "version": "1.0.0",
        "agents": ALL_AGENTS,
        "active_projects": [
            {"slug": p["_slug"], "name": p.get("product", {}).get("name", "unconfigured")}
            for p in projects
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- A2A Task Endpoint ---

@app.post("/tasks/send")
async def send_task(request: Request):
    """A2A task endpoint."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    task_id = body.get("id", f"task-{uuid.uuid4().hex[:12]}")
    message = body.get("message", {})
    parts = message.get("parts", [])

    if not parts:
        raise HTTPException(status_code=400, detail="No message parts provided")

    text = parts[0].get("text", "") if parts else ""
    skill = _detect_skill(text)
    agent = _skill_to_agent(skill)
    preview = text[:200] + ("..." if len(text) > 200 else "")

    # For content-brief skill, check for recent briefs across projects
    if skill == "content-brief":
        briefs = _get_recent_briefs()
        if briefs:
            return {
                "id": task_id,
                "status": {"state": "completed"},
                "artifacts": [
                    {
                        "parts": [
                            {
                                "type": "text",
                                "text": "[Marketing Agent] Recent content briefs:\n"
                                + "\n".join(f"- {b}" for b in briefs)
                                + "\n\nUse GET /output/{project}/{category}/{filename} to read.",
                            }
                        ]
                    }
                ],
            }

    return {
        "id": task_id,
        "status": {"state": "completed"},
        "artifacts": [
            {
                "parts": [
                    {
                        "type": "text",
                        "text": f"[Marketing Agent] Received task for skill '{skill}': {preview}\n\n"
                        f"To execute, run: ./scripts/run-agent.sh {agent}",
                    }
                ]
            }
        ],
    }


def _detect_skill(text: str) -> str:
    """Detect which skill to use based on task text."""
    text_lower = text.lower()
    # SEO skills (check first — more specific)
    if any(w in text_lower for w in ["keyword", "search volume", "trend"]):
        return "keyword-research"
    if any(w in text_lower for w in ["audit", "meta tag", "schema", "structured data", "seo score"]):
        return "content-audit"
    if any(w in text_lower for w in ["competitor", "gap", "backlink"]):
        return "competitor-analysis"
    # Marketing skills
    if any(w in text_lower for w in ["blog", "article", "content", "write", "post"]):
        return "create-content"
    if any(w in text_lower for w in ["social", "twitter", "linkedin", "reddit", "tweet"]):
        return "create-social-posts"
    if any(w in text_lower for w in ["report", "metrics", "performance", "analytics"]):
        return "performance-report"
    if any(w in text_lower for w in ["brief", "outline"]):
        return "content-brief"
    return "weekly-plan"


def _skill_to_agent(skill: str) -> str:
    """Map skill ID to agent name."""
    mapping = {
        "create-content": "content-writer",
        "create-social-posts": "social-media-manager",
        "performance-report": "performance-analyst",
        "weekly-plan": "cmo",
        "keyword-research": "keyword-researcher",
        "content-audit": "content-optimizer",
        "competitor-analysis": "competitor-analyst",
        "content-brief": "competitor-analyst",
    }
    return mapping.get(skill, "cmo")


def _get_recent_briefs() -> list[str]:
    """Get recent content briefs across all projects."""
    briefs = []
    if OUTPUT_DIR.is_dir():
        for project_dir in OUTPUT_DIR.iterdir():
            briefs_dir = project_dir / "briefs"
            if briefs_dir.is_dir():
                for f in sorted(briefs_dir.glob("*.md"), reverse=True)[:3]:
                    if f.name != ".gitkeep":
                        briefs.append(f"{project_dir.name}/{f.name}")
    return briefs[:10]


# --- Output Listing (multi-project) ---

@app.get("/output/{project}/{category}")
async def list_output(project: str, category: str):
    """List generated output files by project and category."""
    output_dir = _safe_output_path(project, category)
    if not output_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"'{project}/{category}' not found")

    files = sorted(output_dir.glob("*.md"), reverse=True)
    return {
        "project": project,
        "category": category,
        "files": [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
            for f in files
            if f.name != ".gitkeep"
        ],
    }


@app.get("/output/{project}/{category}/{filename}")
async def read_output(project: str, category: str, filename: str):
    """Read a specific output file."""
    file_path = _safe_output_path(project, category, filename)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return {"content": file_path.read_text(encoding="utf-8")}


if __name__ == "__main__":
    host = os.environ.get("MARKETING_AGENT_HOST", "127.0.0.1")
    port = int(os.environ.get("MARKETING_AGENT_PORT", "9020"))
    uvicorn.run(app, host=host, port=port)
