"""Project config loader — extracted from a2a_server.py."""

from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent.parent  # marketing-agent/
PROJECTS_DIR = BASE_DIR / "projects"
CONFIG_PROJECTS_DIR = BASE_DIR / "config" / "projects"

# Channel mapping by project type
CHANNEL_MAP = {
    "b2c": {
        "required": [
            "instagram-reels", "tiktok", "youtube-shorts", "naver-blog",
        ],
        "optional": ["twitter", "threads", "newsletter"],
    },
    "b2b": {
        "required": [
            "reddit", "hacker-news", "product-hunt", "indie-hackers",
            "dev-to", "directories",
        ],
        "optional": ["linkedin", "twitter", "youtube-shorts", "newsletter"],
    },
}

# Category → project type mapping
B2C_CATEGORIES = {
    "consumer", "entertainment", "lifestyle", "health", "education",
    "fortune", "astrology", "gaming", "social",
}
B2B_CATEGORIES = {
    "developer-tools", "saas", "devops", "api", "infrastructure",
    "analytics", "security", "productivity", "enterprise",
}


def detect_project_type(project: dict) -> str:
    """Detect B2C or B2B from project config."""
    category = project.get("product", {}).get("category", "").lower()
    if category in B2C_CATEGORIES:
        return "b2c"
    if category in B2B_CATEGORIES:
        return "b2b"
    audience = project.get("audience", {}).get("primary", "").lower()
    dev_keywords = {"developer", "engineer", "devops", "technical", "startup"}
    if any(kw in audience for kw in dev_keywords):
        return "b2b"
    return "b2c"


def get_channels(project: dict) -> dict:
    """Get required and optional channels for a project."""
    ptype = detect_project_type(project)
    return CHANNEL_MAP.get(ptype, CHANNEL_MAP["b2c"])


def load_project(slug: str = "saju") -> dict:
    path = PROJECTS_DIR / f"{slug}.yaml"
    if not path.exists():
        path = CONFIG_PROJECTS_DIR / f"{slug}.yaml"
    if not path.exists():
        fallback = BASE_DIR / "project.yaml"
        if fallback.exists():
            path = fallback
        else:
            return {"_slug": slug}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["_slug"] = slug
    return data


def load_all_projects() -> list[dict]:
    projects = []
    seen_slugs = set()
    for d in [PROJECTS_DIR, CONFIG_PROJECTS_DIR]:
        if d.is_dir():
            for f in sorted(d.glob("*.yaml")):
                if f.stem.startswith("_"):
                    continue
                if f.stem not in seen_slugs:
                    with open(f, encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                        data["_slug"] = f.stem
                        projects.append(data)
                        seen_slugs.add(f.stem)
    if not projects:
        root = BASE_DIR / "project.yaml"
        if root.exists():
            with open(root, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                data["_slug"] = "default"
                projects.append(data)
    return projects
