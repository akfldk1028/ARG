"""Marketing Agent CLI Tools

Unified marketing + SEO tools for multi-project support.

Usage:
    python tools.py web-search "query"
    python tools.py post-slack "message"
    python tools.py list-output content [project-slug]
    python tools.py sitemap-urls "https://example.com/sitemap.xml"
    python tools.py check-meta "https://example.com/page"
    python tools.py list-projects
    python tools.py project-info <project-slug>
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


def _resolve_project_dir(slug: str | None = None) -> Path:
    """Resolve output directory for a project slug."""
    if slug:
        return BASE_DIR / "output" / slug
    return BASE_DIR / "output"


def _load_all_projects() -> list[dict]:
    """Load all project configs from projects/ directory."""
    projects_dir = BASE_DIR / "projects"
    projects = []
    if projects_dir.is_dir():
        for f in sorted(projects_dir.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                data["_slug"] = f.stem
                data["_path"] = str(f)
                projects.append(data)
    # Fallback to root project.yaml
    if not projects:
        root = BASE_DIR / "project.yaml"
        if root.exists():
            with open(root, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
                data["_slug"] = "default"
                data["_path"] = str(root)
                projects.append(data)
    return projects


# --- Web & Search Tools ---


def web_search(query: str) -> str:
    """Search the web using Brave Search API."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return json.dumps({"error": "BRAVE_SEARCH_API_KEY not configured in .env"})

    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": 10},
        headers={"X-Subscription-Token": api_key},
        timeout=10,
    )
    if resp.status_code == 200:
        results = resp.json().get("web", {}).get("results", [])
        return json.dumps(
            [{"title": r["title"], "url": r["url"], "snippet": r.get("description", "")} for r in results],
            ensure_ascii=False,
            indent=2,
        )
    return json.dumps({"error": f"Brave API returned {resp.status_code}"})


def post_slack(message: str) -> str:
    """Post a message to Slack via webhook."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return json.dumps({"error": "SLACK_WEBHOOK_URL not configured"})

    resp = httpx.post(webhook_url, json={"text": message}, timeout=10)
    return json.dumps({"status": resp.status_code, "ok": resp.status_code == 200})


# --- SEO Tools ---


def _validate_url(url: str) -> str | None:
    """Validate URL scheme is http or https. Returns error message or None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Invalid URL scheme: '{parsed.scheme}'. Only http/https allowed."
    return None


def fetch_sitemap_urls(sitemap_url: str) -> str:
    """Fetch and parse URLs from a sitemap.xml."""
    if err := _validate_url(sitemap_url):
        return json.dumps({"error": err})
    try:
        resp = httpx.get(sitemap_url, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            return json.dumps({"error": f"HTTP {resp.status_code}"})

        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        return json.dumps({"count": len(urls), "urls": urls[:50]}, indent=2)
    except httpx.RequestError as e:
        return json.dumps({"error": str(e)})


def check_meta(url: str) -> str:
    """Check meta tags of a URL for SEO audit."""
    if err := _validate_url(url):
        return json.dumps({"error": err})
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        html = resp.text

        def extract(pattern: str) -> str:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else ""

        title = extract(r"<title>(.*?)</title>")
        meta_desc = extract(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']')
        if not meta_desc:
            meta_desc = extract(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']')
        h1_tags = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        img_tags = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
        imgs_no_alt = [t for t in img_tags if 'alt=""' in t or "alt=" not in t]
        canonical = extract(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']')
        og_title = extract(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']')
        og_desc = extract(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']')
        json_ld = re.findall(r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>', html, re.DOTALL)

        return json.dumps(
            {
                "url": url,
                "title": {"text": title, "length": len(title)},
                "meta_description": {"text": meta_desc, "length": len(meta_desc)},
                "h1_count": len(h1_tags),
                "h1_texts": [re.sub(r"<[^>]+>", "", h) for h in h1_tags[:3]],
                "images_total": len(img_tags),
                "images_missing_alt": len(imgs_no_alt),
                "canonical": canonical,
                "og_title": og_title,
                "og_description": og_desc,
                "json_ld_count": len(json_ld),
                "status_code": resp.status_code,
            },
            ensure_ascii=False,
            indent=2,
        )
    except httpx.RequestError as e:
        return json.dumps({"error": str(e)})


# --- Multi-Project Tools ---


def list_projects() -> str:
    """List all configured projects."""
    projects = _load_all_projects()
    return json.dumps(
        [
            {
                "slug": p["_slug"],
                "name": p.get("product", {}).get("name", "unnamed"),
                "category": p.get("product", {}).get("category", "unknown"),
                "config": p["_path"],
            }
            for p in projects
        ],
        ensure_ascii=False,
        indent=2,
    )


def project_info(slug: str) -> str:
    """Show detailed info for a specific project."""
    projects = _load_all_projects()
    for p in projects:
        if p["_slug"] == slug:
            info = {k: v for k, v in p.items() if not k.startswith("_")}
            info["slug"] = p["_slug"]
            # Count output files
            output_dir = BASE_DIR / "output" / slug
            if output_dir.is_dir():
                info["output_counts"] = {}
                for subdir in output_dir.iterdir():
                    if subdir.is_dir():
                        count = len([f for f in subdir.glob("*.md") if f.name != ".gitkeep"])
                        info["output_counts"][subdir.name] = count
            return json.dumps(info, ensure_ascii=False, indent=2, default=str)
    return json.dumps({"error": f"Project '{slug}' not found"})


# --- Output Listing ---


def list_output(category: str, slug: str | None = None) -> str:
    """List output files in a category, optionally filtered by project slug."""
    if slug:
        output_dir = BASE_DIR / "output" / slug / category
    else:
        # List across all projects
        all_files = []
        output_base = BASE_DIR / "output"
        if output_base.is_dir():
            for project_dir in output_base.iterdir():
                cat_dir = project_dir / category
                if cat_dir.is_dir():
                    for f in sorted(cat_dir.glob("*.md"), reverse=True):
                        if f.name != ".gitkeep":
                            all_files.append({"project": project_dir.name, "name": f.name, "size": f.stat().st_size})
        return json.dumps(all_files, indent=2)

    if not output_dir.exists():
        return json.dumps({"error": f"Category '{category}' not found for project '{slug}'"})

    files = sorted(output_dir.glob("*.md"), reverse=True)
    return json.dumps(
        [{"name": f.name, "size": f.stat().st_size} for f in files if f.name != ".gitkeep"],
        indent=2,
    )


# --- CLI ---


_REQUIRES_ARG = {"web-search", "post-slack", "sitemap-urls", "check-meta", "project-info"}


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python tools.py <command> [args]")
        print("Commands: web-search, post-slack, list-output, sitemap-urls, check-meta, list-projects, project-info")
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in _REQUIRES_ARG and not args:
        print(f"Error: '{cmd}' requires an argument.")
        sys.exit(1)

    commands = {
        "web-search": lambda: web_search(args[0]),
        "post-slack": lambda: post_slack(args[0]),
        "list-output": lambda: list_output(args[0] if args else "content", args[1] if len(args) > 1 else None),
        "sitemap-urls": lambda: fetch_sitemap_urls(args[0]),
        "check-meta": lambda: check_meta(args[0]),
        "list-projects": lambda: list_projects(),
        "project-info": lambda: project_info(args[0]),
    }

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    result = commands[cmd]()
    print(result)


if __name__ == "__main__":
    main()
