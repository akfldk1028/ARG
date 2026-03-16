#!/usr/bin/env bash
# run-agent.sh — Run a single agent via Claude Code
# Usage: ./scripts/run-agent.sh <agent-name> [project-slug]
#   agent-name: cmo | content-writer | social-media-manager | performance-analyst
#               | keyword-researcher | content-optimizer | competitor-analyst
#   project-slug: optional, targets a specific project (default: all projects)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

AGENT_NAME="${1:?Usage: run-agent.sh <agent-name> [project-slug]}"
PROJECT_SLUG="${2:-}"
AGENT_FILE="$PROJECT_DIR/.claude/agents/$AGENT_NAME.md"

if [[ ! -f "$AGENT_FILE" ]]; then
    echo "Error: Agent definition not found: $AGENT_FILE"
    echo "Available agents:"
    ls "$PROJECT_DIR/.claude/agents/"
    exit 1
fi

cd "$PROJECT_DIR"

# Build the prompt
TODAY=$(date '+%Y-%m-%d')
AGENT_DEF=$(cat "$AGENT_FILE")

# Determine project context
PROJECT_CONTEXT=""
if [[ -n "$PROJECT_SLUG" ]]; then
    PROJECT_CONTEXT="Your target project slug is: $PROJECT_SLUG
Read project config from projects/$PROJECT_SLUG.yaml (or fallback to project.yaml).
Use output/$PROJECT_SLUG/ for all output.
Use .claude/agent-memory/$PROJECT_SLUG/ for memory."
else
    PROJECT_CONTEXT="Process ALL projects found in the projects/ directory.
If no projects/ directory exists, use the root project.yaml."
fi

PROMPT="$AGENT_DEF

---

You are the $AGENT_NAME agent. Today is $TODAY.
Execute your full workflow as defined above.

$PROJECT_CONTEXT

Follow all rules in .claude/rules/.
Update your memory when done."

# Export PROJECT_SLUG so agent can use it
export PROJECT_SLUG

# Run via Claude Code in headless mode (timeout 10 min)
timeout 600 claude -p "$PROMPT" \
    --allowedTools "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch" \
    --output-format text
