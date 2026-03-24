#!/usr/bin/env bash
# github-push-all.sh — Stage ALL files (including CSV and Excel) and push to GitHub
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

# ── Ensure CSV and Excel are not accidentally ignored ─────────────────────────
# Force-add data files even if any gitignore rule might catch them
git add -f *.csv *.xlsx 2>/dev/null || true

# ── Stage everything else ─────────────────────────────────────────────────────
git add .

# ── Check if there is actually anything to commit ────────────────────────────
if git diff --cached --quiet; then
    echo "Nothing to commit — all files already up to date on GitHub."
    exit 0
fi

# ── Show summary of what will be committed ────────────────────────────────────
echo ""
echo "==> Files to be committed:"
git status --short
echo ""
echo "==> File sizes:"
git diff --cached --name-only | while read -r f; do
    [ -f "$f" ] && du -sh "$f" || echo "  (deleted) $f"
done
echo ""

# ── Prompt for commit message ─────────────────────────────────────────────────
read -rp "Commit message (leave blank for timestamped default): " MSG
if [[ -z "$MSG" ]]; then
    MSG="Update all files — $(date '+%Y-%m-%d %H:%M')"
fi

# ── Commit and push ───────────────────────────────────────────────────────────
echo "==> Committing: \"$MSG\""
git commit -m "$MSG"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "==> Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

echo ""
echo "================================================================"
echo " All files pushed to $(git remote get-url origin)"
echo "================================================================"
