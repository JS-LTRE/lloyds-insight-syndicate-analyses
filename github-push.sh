#!/usr/bin/env bash
# github-push.sh — Stage all changes, commit, and push to GitHub
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [ ! -d ".git" ]; then
    echo "ERROR: Not a git repository. Run ./github-init.sh first."
    exit 1
fi

if ! git remote get-url origin &>/dev/null; then
    echo "ERROR: No remote 'origin' configured. Run ./github-init.sh first."
    exit 1
fi

# ── Check for changes ─────────────────────────────────────────────────────────
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "Nothing to commit — working tree is clean."
    exit 0
fi

# ── Show what will be committed ───────────────────────────────────────────────
echo "==> Changes to be committed:"
git status --short
echo ""

# ── Prompt for commit message ─────────────────────────────────────────────────
read -rp "Commit message (leave blank for timestamped default): " MSG
if [[ -z "$MSG" ]]; then
    MSG="Update — $(date '+%Y-%m-%d %H:%M')"
fi

# ── Stage, commit, push ───────────────────────────────────────────────────────
echo "==> Staging all files..."
git add .

echo "==> Committing: \"$MSG\""
git commit -m "$MSG"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "==> Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

echo ""
echo "================================================================"
echo " Pushed successfully to $(git remote get-url origin)"
echo "================================================================"
