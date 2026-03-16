#!/usr/bin/env bash
# run.sh — Run the full daily 7-agent marketing cycle
# Usage: ./scripts/run.sh [--agent AGENT_NAME] [--project PROJECT_SLUG]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/schedules/cron-log.md"

cd "$PROJECT_DIR"

PROJECT_SLUG=""
SINGLE_AGENT=""

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --agent)
            SINGLE_AGENT="$2"
            shift 2
            ;;
        --project)
            PROJECT_SLUG="$2"
            shift 2
            ;;
        *)
            echo "Usage: run.sh [--agent AGENT_NAME] [--project PROJECT_SLUG]"
            exit 1
            ;;
    esac
done

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $*" | tee -a "$LOG_FILE"
}

run_agent() {
    local agent_name="$1"
    log "Starting agent: $agent_name ${PROJECT_SLUG:+(project: $PROJECT_SLUG)}"
    "$SCRIPT_DIR/run-agent.sh" "$agent_name" ${PROJECT_SLUG:+"$PROJECT_SLUG"}
    log "Completed agent: $agent_name"
}

# If --agent flag is passed, run single agent
if [[ -n "$SINGLE_AGENT" ]]; then
    run_agent "$SINGLE_AGENT"
    exit 0
fi

# Full daily cycle: 7 agents in optimal order
# SEO research first → strategy → content → optimization → distribution → analysis
log "=== Daily Marketing Cycle Starting ==="

run_agent "keyword-researcher"      # 06:00 — SEO research first
run_agent "cmo"                     # 07:00 — Strategy with keyword data
run_agent "content-writer"          # 09:00 — Write content
run_agent "content-optimizer"       # 11:00 — Audit written content
run_agent "social-media-manager"    # 13:00 — Distribute to social
run_agent "competitor-analyst"      # 16:00 — Competitor intel for next cycle
run_agent "performance-analyst"     # 18:00 — Daily report

log "=== Daily Marketing Cycle Complete ==="
