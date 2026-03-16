# Universal Marketing Agent System

AI-powered marketing + SEO team that can promote **any project** — open source tools, SaaS products, consumer apps, or enterprise software.

7 autonomous agents run on a daily cron cycle via [Claude Code](https://claude.com/claude-code) headless mode.

## Quick Start

```bash
# Initialize a project
./scripts/init.sh "My Awesome Tool"

# Or auto-fill from an existing repo
./scripts/init.sh "My Awesome Tool" --from-repo /path/to/repo

# Edit the generated config
$EDITOR projects/my-awesome-tool.yaml

# Set up API keys
cp .env.example .env
$EDITOR .env

# Run a single agent
./scripts/run-agent.sh cmo my-awesome-tool

# Run the full daily cycle
./scripts/run.sh --project my-awesome-tool

# Install cron for autonomous operation
./scripts/setup-cron.sh
```

## Multi-Project Support

Each project is a YAML file in `projects/`. Agents process all projects unless scoped:

```bash
# Target one project
./scripts/run-agent.sh content-writer my-saas-app

# All projects
./scripts/run-agent.sh content-writer
```

### Project Categories

The `product.category` field in your YAML drives content and distribution strategy:

| Category | Content Style | Distribution |
|----------|--------------|-------------|
| `developer-tools` | Tutorials, API docs, benchmarks | GitHub, r/programming, HN |
| `saas` | Case studies, ROI, comparisons | LinkedIn, product updates |
| `consumer` | How-to, user stories, tips | Instagram, TikTok-style |
| `enterprise` | Whitepapers, compliance, reports | LinkedIn, media outreach |
| `open-source` | Release notes, contributor guides | HN, r/opensource, newsletters |

## Agents (7)

| Agent | Schedule | Role |
|-------|----------|------|
| **Keyword Researcher** | 06:00 | Discover keywords, analyze search intent |
| **CMO** | 07:00 | Daily strategy, task assignments |
| **Content Writer** | 09:00 | Blog posts, marketing copy |
| **Content Optimizer** | 11:00 | SEO audit of generated content |
| **Social Media Manager** | 13:00 | Platform-specific social posts |
| **Competitor Analyst** | 16:00 | Competitive intel, content briefs |
| **Performance Analyst** | 18:00 | Daily metrics report |

## Output Structure

```
output/{project-slug}/
├── content/    # Blog posts, articles
├── social/     # Platform-specific posts
├── reports/    # Performance reports
├── images/     # Image descriptions
├── keywords/   # Keyword research
├── audits/     # SEO audit reports
└── briefs/     # Content briefs from competitor analysis
```

All output is draft-only — no automated publishing.

## A2A Protocol

The system exposes an [A2A](https://google.github.io/A2A/) server for agent-to-agent communication:

```bash
python a2a_server.py
# GET  http://localhost:9020/.well-known/agent.json  — agent card (8 skills)
# POST http://localhost:9020/tasks/send               — send a task
# GET  http://localhost:9020/health                    — health + active projects
# GET  http://localhost:9020/output/{project}/{category} — list outputs
```

## CLI Tools

```bash
python tools.py list-projects                     # Show all configured projects
python tools.py project-info my-product           # Project details + output counts
python tools.py web-search "multi-agent systems"  # Brave Search API
python tools.py sitemap-urls "https://example.com/sitemap.xml"
python tools.py check-meta "https://example.com"  # SEO meta tag audit
python tools.py list-output content my-product    # List content files
python tools.py post-slack "Deploy complete"      # Slack notification
```

## Configuration

### Project YAML

See `project.example.yaml` for all options. Key sections:

- `product` — name, tagline, website, category
- `audience` — primary/secondary, pain points, value props
- `brand` — tone, language, emoji policy
- `social` — Twitter/LinkedIn/Reddit handles and enabled flags
- `seo` — primary keywords, competitor domains
- `schedule` — content days, timezone

### Environment Variables

See `.env.example`. Required: `BRAVE_SEARCH_API_KEY` for web search.

## How It Works

Each agent is a markdown file in `.claude/agents/` that defines:
1. Responsibilities
2. Project resolution logic (multi-project aware)
3. Step-by-step workflow
4. Output format
5. Rules

Agents run via Claude Code headless mode (`claude -p`), reading their own definition as the prompt. They have access to Read, Write, Edit, Glob, Grep, WebSearch, and WebFetch tools.

State persists across runs via `.claude/agent-memory/{project}/` files. Strategy coordination happens through `schedules/daily.md` and `schedules/weekly.md`.
