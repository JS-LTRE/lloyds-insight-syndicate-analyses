#!/usr/bin/env bash
# github-status.sh — Check if this folder is linked to a GitHub repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=== Git repo check ==="
if [ ! -d ".git" ]; then
    echo "FAIL: No .git folder found — this directory is not a git repository."
    echo "      Run ./github-init.sh to set it up."
    exit 1
fi
echo "PASS: .git folder exists."

echo ""
echo "=== Remote check ==="
if ! git remote get-url origin &>/dev/null; then
    echo "FAIL: No remote 'origin' configured."
    echo "      Run: git remote add origin <your-github-url>"
    exit 1
fi
REMOTE_URL=$(git remote get-url origin)
echo "PASS: Remote 'origin' is set to: $REMOTE_URL"

echo ""
echo "=== Branch check ==="
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
echo "INFO: Current branch: $BRANCH"

echo ""
echo "=== Commit check ==="
COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo 0)
LAST_COMMIT=$(git log -1 --format="%h — %s (%ar)" 2>/dev/null || echo "none")
echo "INFO: Total commits: $COMMIT_COUNT"
echo "INFO: Last commit:   $LAST_COMMIT"

echo ""
echo "=== GitHub connectivity check ==="
echo "     Testing connection to remote..."
if git ls-remote origin HEAD &>/dev/null; then
    echo "PASS: Successfully connected to GitHub remote."
else
    echo "FAIL: Could not reach the remote. Possible causes:"
    echo "      - Repo does not exist on GitHub yet"
    echo "      - Authentication issue (SSH key or HTTPS token)"
    echo "      - Wrong remote URL"
    echo ""
    echo "      Current remote URL: $REMOTE_URL"
    echo "      To fix:  git remote set-url origin <correct-url>"
    exit 1
fi

echo ""
echo "=== Push status ==="
git fetch origin "$BRANCH" 2>/dev/null || true
LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "none")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "PASS: Local branch is in sync with origin/$BRANCH."
elif [ "$REMOTE" = "none" ]; then
    echo "WARN: Branch '$BRANCH' has not been pushed to GitHub yet."
    echo "      Run: git push -u origin $BRANCH"
else
    AHEAD=$(git rev-list "origin/$BRANCH..HEAD" --count 2>/dev/null || echo "?")
    echo "WARN: Local branch is $AHEAD commit(s) ahead of origin/$BRANCH."
    echo "      Run: git push"
fi

echo ""
echo "================================================================"
echo " Summary: repo is linked to $REMOTE_URL"
echo "================================================================"
