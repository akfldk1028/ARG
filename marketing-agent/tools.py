"""Marketing Agent CLI Tools

Unified marketing + SEO + SNS tools for multi-project support.

Usage:
    python tools.py web-search "query"
    python tools.py post-slack "message"
    python tools.py list-output content [project-slug]
    python tools.py sitemap-urls "https://example.com/sitemap.xml"
    python tools.py check-meta "https://example.com/page"
    python tools.py list-projects
    python tools.py project-info <project-slug>
    python tools.py ig-reels-upload <video_url> <caption>
    python tools.py tiktok-upload <video_url> <title> [privacy_level]
    python tools.py yt-shorts-upload <video_path> <title> [description]
    python tools.py reddit-comment <text> [subreddit] [parent_id]
    python tools.py devto-post <title> <body_markdown> [tags]
    python tools.py naver-blog-post <title> <contents>
    python tools.py newsletter-send <subject> <html> <to>
    python tools.py directory-submit <dir_name> <product_name> <product_url> <desc>
    python tools.py twitter-post <text>
    python tools.py linkedin-post <text>
"""

import json
import os
import re
import sys
import time
from datetime import datetime
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


# --- SNS Upload Tools ---


def ig_reels_upload(video_url: str, caption: str) -> str:
    """Upload video to Instagram Reels (graph.instagram.com v25.0)."""
    ig_user_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not ig_user_id or not token:
        return json.dumps({"error": "INSTAGRAM_ACCOUNT_ID and INSTAGRAM_ACCESS_TOKEN required in .env"})

    # 1. Create media container
    resp = httpx.post(
        f"https://graph.instagram.com/v25.0/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    if resp.status_code != 200:
        return json.dumps({"error": f"Container creation failed ({resp.status_code})", "detail": resp.text})
    container_id = resp.json()["id"]

    # 2. Poll until FINISHED (60s interval, max 5 attempts)
    for _attempt in range(5):
        time.sleep(60)
        st = httpx.get(
            f"https://graph.instagram.com/v25.0/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        ).json().get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            return json.dumps({"error": "Container processing failed", "container_id": container_id})
    else:
        return json.dumps({"error": "Timeout waiting for container (5min)", "container_id": container_id})

    # 3. Publish
    pub = httpx.post(
        f"https://graph.instagram.com/v25.0/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    if pub.status_code != 200:
        return json.dumps({"error": f"Publish failed ({pub.status_code})", "detail": pub.text})
    return json.dumps({"post_id": pub.json()["id"], "container_id": container_id, "status": "PUBLISHED"}, indent=2)


def tiktok_upload(video_url: str, title: str, privacy_level: str = "SELF_ONLY") -> str:
    """Upload video to TikTok via Content Posting API v2."""
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    if not token:
        return json.dumps({"error": "TIKTOK_ACCESS_TOKEN required in .env"})

    # 1. Init publish
    resp = httpx.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "post_info": {"title": title, "privacy_level": privacy_level},
            "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
        },
        timeout=30,
    )
    if resp.status_code != 200:
        return json.dumps({"error": f"TikTok init failed ({resp.status_code})", "detail": resp.text})
    publish_id = resp.json().get("data", {}).get("publish_id")
    if not publish_id:
        return json.dumps({"error": "No publish_id returned", "response": resp.json()})

    # 2. Poll status (30s interval, max 10 attempts)
    for _attempt in range(10):
        time.sleep(30)
        st_resp = httpx.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"publish_id": publish_id},
            timeout=15,
        )
        status = st_resp.json().get("data", {}).get("status")
        if status == "PUBLISH_COMPLETE":
            return json.dumps({"publish_id": publish_id, "status": "PUBLISH_COMPLETE"}, indent=2)
        if status == "FAILED":
            return json.dumps({"error": "TikTok publish failed", "publish_id": publish_id, "detail": st_resp.text})
    return json.dumps({"error": "Timeout (5min)", "publish_id": publish_id})


def yt_shorts_upload(video_file_path: str, title: str, description: str = "") -> str:
    """Upload YouTube Shorts via YouTube Data API v3 resumable upload."""
    token = os.environ.get("YOUTUBE_ACCESS_TOKEN")
    if not token:
        return json.dumps({"error": "YOUTUBE_ACCESS_TOKEN required in .env"})

    if "#Shorts" not in title:
        title = f"{title} #Shorts"

    metadata = {
        "snippet": {"title": title, "description": description, "categoryId": "22"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }

    # 1. Init resumable upload
    init_resp = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=metadata,
        timeout=30,
    )
    if init_resp.status_code != 200:
        return json.dumps({"error": f"YT init failed ({init_resp.status_code})", "detail": init_resp.text})

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        return json.dumps({"error": "No upload URL in response headers"})

    # 2. Upload video file
    video_path = Path(video_file_path)
    if not video_path.exists():
        return json.dumps({"error": f"File not found: {video_file_path}"})

    with open(video_path, "rb") as f:
        up_resp = httpx.put(upload_url, content=f.read(), headers={"Content-Type": "video/mp4"}, timeout=300)
    if up_resp.status_code not in (200, 201):
        return json.dumps({"error": f"YT upload failed ({up_resp.status_code})", "detail": up_resp.text})

    data = up_resp.json()
    video_id = data.get("id", "")
    return json.dumps({
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
        "status": data.get("status", {}).get("uploadStatus"),
    }, indent=2)


# --- Community / Blog Tools ---


def reddit_comment(text: str, subreddit: str = "", parent_id: str = "", title: str = "", kind: str = "comment") -> str:
    """Post comment or submission to Reddit via OAuth2."""
    # Validate params before making any network calls
    if kind == "comment" and not parent_id:
        return json.dumps({"error": "comment requires parent_id; self/link requires subreddit"})
    if kind in ("self", "link") and not subreddit:
        return json.dumps({"error": "comment requires parent_id; self/link requires subreddit"})

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    refresh_token = os.environ.get("REDDIT_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        return json.dumps({"error": "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_REFRESH_TOKEN required in .env"})

    # OAuth2 token exchange
    auth_resp = httpx.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"User-Agent": "marketing-agent/1.0"},
        timeout=15,
    )
    if auth_resp.status_code != 200:
        return json.dumps({"error": f"Reddit auth failed ({auth_resp.status_code})"})
    access_token = auth_resp.json().get("access_token")
    headers = {"Authorization": f"bearer {access_token}", "User-Agent": "marketing-agent/1.0"}

    if kind == "comment":
        resp = httpx.post(
            "https://oauth.reddit.com/api/comment",
            headers=headers,
            data={"thing_id": parent_id, "text": text},
            timeout=15,
        )
    else:
        payload = {"sr": subreddit, "kind": kind, "title": title or text[:100]}
        if kind == "self":
            payload["text"] = text
        else:
            payload["url"] = text
        resp = httpx.post("https://oauth.reddit.com/api/submit", headers=headers, data=payload, timeout=15)

    if resp.status_code != 200:
        return json.dumps({"error": f"Reddit failed ({resp.status_code})", "detail": resp.text})
    return json.dumps(resp.json(), ensure_ascii=False, indent=2)


def devto_post(title: str, body_markdown: str, tags: str = "", published: bool = False) -> str:
    """Create article on Dev.to."""
    api_key = os.environ.get("DEVTO_API_KEY")
    if not api_key:
        return json.dumps({"error": "DEVTO_API_KEY required in .env"})

    article: dict = {"title": title, "body_markdown": body_markdown, "published": published}
    if tags:
        article["tags"] = [t.strip() for t in tags.split(",")][:4]

    resp = httpx.post(
        "https://dev.to/api/articles",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={"article": article},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        return json.dumps({"error": f"Dev.to failed ({resp.status_code})", "detail": resp.text})
    data = resp.json()
    return json.dumps({"id": data.get("id"), "url": data.get("url"), "slug": data.get("slug")}, indent=2)


def naver_blog_post(title: str, contents: str) -> str:
    """Post to Naver Blog via Open API."""
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    token = os.environ.get("NAVER_BLOG_ACCESS_TOKEN")
    if not all([client_id, client_secret, token]):
        return json.dumps({"error": "NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_BLOG_ACCESS_TOKEN required in .env"})

    resp = httpx.post(
        "https://openapi.naver.com/blog/writePost.json",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
        data={"title": title, "contents": contents},
        timeout=30,
    )
    if resp.status_code != 200:
        return json.dumps({"error": f"Naver blog failed ({resp.status_code})", "detail": resp.text})
    data = resp.json()
    return json.dumps({"log_no": data.get("log_no"), "url": data.get("url")}, ensure_ascii=False, indent=2)


def newsletter_send(subject: str, html: str, to: str = "") -> str:
    """Send email newsletter via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    if not api_key:
        return json.dumps({"error": "RESEND_API_KEY required in .env"})
    recipients = [t.strip() for t in to.split(",")] if to else []
    if not recipients:
        return json.dumps({"error": "Recipient email(s) required (comma-separated)"})

    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"from": sender, "to": recipients, "subject": subject, "html": html},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        return json.dumps({"error": f"Resend failed ({resp.status_code})", "detail": resp.text})
    return json.dumps({"id": resp.json().get("id"), "status": "sent"}, indent=2)


def directory_submit(directory_name: str, product_name: str, product_url: str, description_short: str) -> str:
    """Log SaaS directory submission for tracking (browser automation placeholder)."""
    record = {
        "directory": directory_name,
        "product": product_name,
        "url": product_url,
        "description": description_short,
        "status": "pending",
        "submitted_at": datetime.now().isoformat(),
        "notes": "Manual/browser submission required — logged for tracking",
    }
    log_dir = BASE_DIR / "output" / "directory-submissions"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{directory_name.lower().replace(' ', '-')}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return json.dumps(record, ensure_ascii=False, indent=2)


# --- Social Text Tools ---


def twitter_post(text: str, reply_to: str = "") -> str:
    """Post tweet via Twitter/X API v2. Requires OAuth 2.0 user access token (not app-only bearer)."""
    token = os.environ.get("TWITTER_ACCESS_TOKEN") or os.environ.get("TWITTER_BEARER_TOKEN")
    if not token:
        return json.dumps({"error": "TWITTER_ACCESS_TOKEN required in .env (OAuth 2.0 user token, not app-only bearer)"})

    payload: dict = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}

    resp = httpx.post(
        "https://api.twitter.com/2/tweets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        return json.dumps({"error": f"Twitter failed ({resp.status_code})", "detail": resp.text})
    data = resp.json().get("data", {})
    tweet_id = data.get("id", "")
    return json.dumps({"tweet_id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}, indent=2)


def linkedin_post(text: str, author_urn: str = "") -> str:
    """Post to LinkedIn via UGC Posts API."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        return json.dumps({"error": "LINKEDIN_ACCESS_TOKEN required in .env"})
    if not author_urn:
        author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", "")
    if not author_urn:
        return json.dumps({"error": "LINKEDIN_AUTHOR_URN required (urn:li:person:xxx)"})

    resp = httpx.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json={
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        return json.dumps({"error": f"LinkedIn failed ({resp.status_code})", "detail": resp.text})
    post_id = resp.headers.get("X-RestLi-Id", resp.json().get("id", ""))
    return json.dumps({"post_id": post_id, "status": "PUBLISHED"}, indent=2)


# --- CLI ---


_REQUIRES_ARG = {
    "web-search", "post-slack", "sitemap-urls", "check-meta", "project-info",
    "ig-reels-upload", "tiktok-upload", "yt-shorts-upload", "reddit-comment",
    "devto-post", "naver-blog-post", "newsletter-send", "directory-submit",
    "twitter-post", "linkedin-post",
}


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print("Usage: python tools.py <command> [args]")
        print("Commands: web-search, post-slack, list-output, sitemap-urls, check-meta, list-projects, project-info,")
        print("         ig-reels-upload, tiktok-upload, yt-shorts-upload, reddit-comment, devto-post,")
        print("         naver-blog-post, newsletter-send, directory-submit, twitter-post, linkedin-post")
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
        # SNS Upload
        "ig-reels-upload": lambda: ig_reels_upload(args[0], args[1] if len(args) > 1 else ""),
        "tiktok-upload": lambda: tiktok_upload(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "SELF_ONLY"),
        "yt-shorts-upload": lambda: yt_shorts_upload(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""),
        # Community / Blog
        "reddit-comment": lambda: reddit_comment(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""),
        "devto-post": lambda: devto_post(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""),
        "naver-blog-post": lambda: naver_blog_post(args[0], args[1] if len(args) > 1 else ""),
        "newsletter-send": lambda: newsletter_send(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""),
        "directory-submit": lambda: directory_submit(args[0], args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else "", args[3] if len(args) > 3 else ""),
        # Social Text
        "twitter-post": lambda: twitter_post(args[0], args[1] if len(args) > 1 else ""),
        "linkedin-post": lambda: linkedin_post(args[0], args[1] if len(args) > 1 else ""),
    }

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    result = commands[cmd]()
    print(result)


if __name__ == "__main__":
    main()
