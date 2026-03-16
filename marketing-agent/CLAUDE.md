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
| cmo | Strategy, assignments | schedules/daily.md |
| content-writer | Blog posts, copy | output/{slug}/content/ |
| social-media-manager | Social posts | output/{slug}/social/ |
| performance-analyst | Reports, metrics | output/{slug}/reports/ |
| keyword-researcher | Keyword discovery | output/{slug}/keywords/ |
| content-optimizer | SEO audits | output/{slug}/audits/ |
| competitor-analyst | Competitor briefs | output/{slug}/briefs/ |

## Rules (8)
brand-voice, cms-schema, image-guidelines, platform-rules, utm-rules,
keyword-strategy, schema-markup, seo-checklist

## A2A Server
- Port: 9020
- Agent card: `GET http://localhost:9020/.well-known/agent.json`
- 8 skills: create-content, create-social-posts, performance-report, weekly-plan,
  keyword-research, content-audit, competitor-analysis, content-brief
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
- `schedules/` — living documents updated by agents
- `.claude/agent-memory/{slug}/` — persistent agent state
- `.claude/rules/` — immutable policies
- `.claude/agents/` — agent definitions (7 agents)
