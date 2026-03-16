#!/usr/bin/env bash
# init.sh — Initialize a new project for the marketing agent system
# Usage: ./scripts/init.sh <project-name> [--from-repo <path>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PROJECT_NAME="${1:?Usage: init.sh <project-name> [--from-repo <path>]}"
# Slugify: lowercase, replace spaces/special chars with hyphens
SLUG=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')

REPO_PATH=""
if [[ "${2:-}" == "--from-repo" ]] && [[ -n "${3:-}" ]]; then
    REPO_PATH="$3"
fi

echo "Initializing project: $PROJECT_NAME (slug: $SLUG)"

# 1. Create project config from template
PROJECTS_DIR="$PROJECT_DIR/projects"
mkdir -p "$PROJECTS_DIR"
PROJECT_YAML="$PROJECTS_DIR/$SLUG.yaml"

if [[ -f "$PROJECT_YAML" ]]; then
    echo "Warning: $PROJECT_YAML already exists. Skipping config creation."
else
    cp "$PROJECT_DIR/project.example.yaml" "$PROJECT_YAML"

    # If --from-repo, try to extract name/tagline
    if [[ -n "$REPO_PATH" ]]; then
        # Try package.json
        if [[ -f "$REPO_PATH/package.json" ]]; then
            PKG_NAME=$(python3 -c "import json; d=json.load(open('$REPO_PATH/package.json')); print(d.get('name',''))" 2>/dev/null || true)
            PKG_DESC=$(python3 -c "import json; d=json.load(open('$REPO_PATH/package.json')); print(d.get('description',''))" 2>/dev/null || true)
            if [[ -n "$PKG_NAME" ]]; then
                sed -i "s/name: \"My Product\"/name: \"$PKG_NAME\"/" "$PROJECT_YAML"
            fi
            if [[ -n "$PKG_DESC" ]]; then
                sed -i "s/tagline: \"One-line description of what it does\"/tagline: \"$PKG_DESC\"/" "$PROJECT_YAML"
            fi
            echo "  Extracted metadata from package.json"
        # Try pyproject.toml
        elif [[ -f "$REPO_PATH/pyproject.toml" ]]; then
            PY_NAME=$(grep '^name' "$REPO_PATH/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/' || true)
            PY_DESC=$(grep '^description' "$REPO_PATH/pyproject.toml" | head -1 | sed 's/.*= *"\(.*\)"/\1/' || true)
            if [[ -n "$PY_NAME" ]]; then
                sed -i "s/name: \"My Product\"/name: \"$PY_NAME\"/" "$PROJECT_YAML"
            fi
            if [[ -n "$PY_DESC" ]]; then
                sed -i "s/tagline: \"One-line description of what it does\"/tagline: \"$PY_DESC\"/" "$PROJECT_YAML"
            fi
            echo "  Extracted metadata from pyproject.toml"
        fi
    fi
    echo "  Created: $PROJECT_YAML"
fi

# 2. Create output directories
OUTPUT_DIR="$PROJECT_DIR/output/$SLUG"
for subdir in content social reports images keywords audits briefs; do
    mkdir -p "$OUTPUT_DIR/$subdir"
    touch "$OUTPUT_DIR/$subdir/.gitkeep"
done
echo "  Created: output/$SLUG/ (7 subdirectories)"

# 3. Create per-project agent memory
MEMORY_DIR="$PROJECT_DIR/.claude/agent-memory/$SLUG"
mkdir -p "$MEMORY_DIR"
for agent in cmo content social performance keyword optimizer competitor; do
    MEMORY_FILE="$MEMORY_DIR/$agent-memory.md"
    if [[ ! -f "$MEMORY_FILE" ]]; then
        echo "# ${agent^} Agent Memory — $PROJECT_NAME" > "$MEMORY_FILE"
        echo "" >> "$MEMORY_FILE"
        echo "Project: $SLUG" >> "$MEMORY_FILE"
        echo "Initialized: $(date '+%Y-%m-%d')" >> "$MEMORY_FILE"
        echo "" >> "$MEMORY_FILE"
        echo "## Log" >> "$MEMORY_FILE"
    fi
done
echo "  Created: .claude/agent-memory/$SLUG/ (7 memory files)"

echo ""
echo "Done! Next steps:"
echo "  1. Edit projects/$SLUG.yaml with your product details"
echo "  2. Run: ./scripts/run-agent.sh cmo $SLUG"
echo "  3. Or run all agents: ./scripts/run.sh"
