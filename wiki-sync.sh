#!/usr/bin/env bash
# Wiki Git Auto-Sync — called by cron or manually
set -euo pipefail

WIKI_DIR="$HOME/.hermes/wiki"
cd "$WIKI_DIR"

# Stage all changes
git add -A

# Check if there's anything to commit
if git diff --cached --quiet; then
    echo "[$(date)] No changes to sync"
    exit 0
fi

# Commit with timestamp
git commit -m "sync: $(date +%Y-%m-%d_%H%M%S)"

# Push
git push origin master

echo "[$(date)] Wiki synced to GitHub"
