#!/usr/bin/env bash
# setup-cron.sh — Install cron jobs for the 7-agent marketing team
# Usage: ./scripts/setup-cron.sh [--remove]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RUN_SCRIPT="$SCRIPT_DIR/run.sh"
CRON_TAG="# marketing-agent"

remove_cron() {
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
    echo "Removed marketing-agent cron jobs."
}

if [[ "${1:-}" == "--remove" ]]; then
    remove_cron
    exit 0
fi

# Remove existing entries first (both old marketing-agent and seo-agent tags)
remove_cron 2>/dev/null || true
crontab -l 2>/dev/null | grep -v "# seo-agent" | crontab - 2>/dev/null || true

# Read timezone from project config (check projects/ first, then root)
if [[ -d "$PROJECT_DIR/projects" ]]; then
    FIRST_YAML=$(ls "$PROJECT_DIR/projects/"*.yaml 2>/dev/null | head -1)
    if [[ -n "$FIRST_YAML" ]]; then
        TZ_LINE=$(grep 'timezone:' "$FIRST_YAML" | head -1 | awk '{print $2}' | tr -d '"')
    fi
fi
if [[ -z "${TZ_LINE:-}" ]] && [[ -f "$PROJECT_DIR/project.yaml" ]]; then
    TZ_LINE=$(grep 'timezone:' "$PROJECT_DIR/project.yaml" | head -1 | awk '{print $2}' | tr -d '"')
fi
TZ="${TZ_LINE:-UTC}"

# Install 7 agent cron jobs
(crontab -l 2>/dev/null; cat <<EOF
CRON_TZ=$TZ $CRON_TAG
0 6 * * * $RUN_SCRIPT --agent keyword-researcher $CRON_TAG
0 7 * * * $RUN_SCRIPT --agent cmo $CRON_TAG
0 9 * * * $RUN_SCRIPT --agent content-writer $CRON_TAG
0 11 * * * $RUN_SCRIPT --agent content-optimizer $CRON_TAG
0 13 * * * $RUN_SCRIPT --agent social-media-manager $CRON_TAG
0 16 * * * $RUN_SCRIPT --agent competitor-analyst $CRON_TAG
0 18 * * * $RUN_SCRIPT --agent performance-analyst $CRON_TAG
EOF
) | crontab -

echo "Installed 7-agent marketing cron jobs (TZ=$TZ):"
echo "  06:00 — Keyword Researcher    (SEO research)"
echo "  07:00 — CMO                   (strategy with keyword data)"
echo "  09:00 — Content Writer        (write content)"
echo "  11:00 — Content Optimizer     (SEO audit)"
echo "  13:00 — Social Media Manager  (distribute)"
echo "  16:00 — Competitor Analyst    (competitive intel)"
echo "  18:00 — Performance Analyst   (daily report)"
echo ""
echo "To remove: $0 --remove"
echo "To verify: crontab -l"
