#!/bin/bash
# Auto backup script for OpenClaw workspace
# Run: chmod +x backup.sh && ./backup.sh

cd ~/.openclaw/workspace

# Add all changes
git add -A

# Check if there are changes
if git diff --staged --quiet; then
    echo "$(date): No changes to commit"
    exit 0
fi

# Commit with timestamp
git commit -m "Auto backup $(date '+%Y-%m-%d %H:%M')"

# Push to remote
git push origin main

echo "$(date): Backup completed"
