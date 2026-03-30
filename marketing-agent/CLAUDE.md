# Marketing Agent Team

## Overview
Universal AI marketing + SEO team. Supports multiple projects simultaneously.
7 agents, all pure markdown — zero code in agent logic.

## Architecture
```
Keyword Researcher (06:00) → discover keywords
CMO (07:00)                → strategy + daily assignments
Content Writer (09:00)     → blog posts + copy
Content Optimizer (11:00)  → SEO audit of content
Social Media Manager (13:00) → social posts
Competitor Analyst (16:00) → competitive intel + briefs
Performance Analyst (18:00) → daily report
```

> **사주(saju) 프로젝트**: 위 스케줄 대신 zeroclaw SOP + n8n 웹훅으로 트리거.
> 매일 09:30 KST에 zeroclaw가 A2A 서버를 호출하여 콘텐츠 생성 → n8n → 영상 → SNS.

## Quick Start
```bash
# 1. Initialize a project
./scripts/init.sh "My Product"
# or auto-fill from repo:
./scripts/init.sh "My Product" --from-repo /path/to/repo

# 2. Edit project config
$EDITOR projects/my-product.yaml

# 3. Add API keys
cp .env.example .env && $EDITOR .env

# 4. Run agents
./scripts/run-agent.sh cmo my-product          # single agent, single project
./scripts/run.sh --project my-product          # full cycle, single project
./scripts/run.sh                                # full cycle, all projects

# 5. (Optional) Install cron
./scripts/setup-cron.sh
```

## Multi-Project Support
Each project gets:
- `projects/{slug}.yaml` — config
- `output/{slug}/` — 7 output subdirs (content, social, reports, images, keywords, audits, briefs)
- `.claude/agent-memory/{slug}/` — 7 memory files

Project resolution order (in agents):
1. `PROJECT_SLUG` env var → `projects/{slug}.yaml`
2. `projects/` directory exists → iterate all YAML files
3. Fallback: root `project.yaml` (backward compatible)

## Agents (7)

| Agent | Role | Output |
|-------|------|--------|
| cmo | Strategy, assignments | `output/{slug}/schedules/{date}-daily-plan.md` |
| keyword-researcher | Keyword discovery | `output/{slug}/keywords/` |
| content-writer | Blog posts, copy, scenes | `output/{slug}/content/` |
| content-optimizer | SEO audits | `output/{slug}/audits/` |
| social-media-manager | Social posts (IG/TikTok) | `output/{slug}/social/` |
| competitor-analyst | Competitor briefs | `output/{slug}/briefs/` |
| performance-analyst | Reports, metrics | `output/{slug}/reports/` |

## Rules (8)
brand-voice, cms-schema, image-guidelines, platform-rules, utm-rules,
keyword-strategy, schema-markup, seo-checklist

## Package Structure
```
marketing_agent/           # Python package
  __init__.py
  models.py                # Pydantic: Scene, ContentConfig, ContentRequest, ContentResponse
  templates.py             # 31 saju templates + date rotation
  generator.py             # ContentGenerator.create() → ContentResponse
  config.py                # project yaml loader
  routes/
    __init__.py            # create_app() factory
    content.py             # POST /api/content/create, /api/content/audit
    agent_card.py          # GET /.well-known/agent.json, /health
    output.py              # GET /output/{project}/{category}
tests/
  test_models.py
  test_templates.py
  test_generator.py
  test_api.py
```

## A2A Server
- Port: 9020 (`python a2a_server.py`)
- Agent card: `GET http://localhost:9020/.well-known/agent.json`
- Content API: `POST /api/content/create` → `{title, hashtags, scenes[], config}`
- Content Audit: `POST /api/content/audit` → pass-through (Phase 1)
- Multi-project output: `GET /output/{project}/{category}`

## CLI Tools
```bash
python tools.py web-search "query"
python tools.py sitemap-urls "https://example.com/sitemap.xml"
python tools.py check-meta "https://example.com/page"
python tools.py list-output content [project-slug]
python tools.py list-projects
python tools.py project-info <slug>
python tools.py post-slack "message"
```

## Directory Convention
- `projects/` — per-project YAML configs (git-ignored)
- `output/{slug}/` — generated deliverables (git-ignored)
- `schedules/` — living template documents (CMO references only)
- `.claude/agent-memory/{slug}/` — persistent agent state
- `.claude/rules/` — immutable policies
- `.claude/agents/` — agent definitions (7 agents)