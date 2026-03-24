#!/usr/bin/env bash
# github-init.sh — Initialise this folder as a Git repo and push to GitHub
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Prompt for GitHub repo URL ────────────────────────────────────────────────
echo ""
echo "Enter your GitHub remote URL."
echo "  HTTPS example: https://github.com/your-org/your-repo.git"
echo "  SSH example:   git@github.com:your-org/your-repo.git"
echo ""
read -rp "GitHub URL: " REMOTE_URL

if [[ -z "$REMOTE_URL" ]]; then
    echo "ERROR: No URL provided. Exiting."
    exit 1
fi

# ── Create .gitignore ─────────────────────────────────────────────────────────
echo "==> Writing .gitignore..."
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.env
.DS_Store
*.log
nginx/
EOF

# ── Initialise git repo ───────────────────────────────────────────────────────
if [ ! -d ".git" ]; then
    echo "==> Initialising git repository..."
    git init -b main
else
    echo "==> Git repository already initialised."
fi

# ── Configure remote ─────────────────────────────────────────────────────────
if git remote get-url origin &>/dev/null; then
    echo "==> Updating existing remote 'origin' to $REMOTE_URL"
    git remote set-url origin "$REMOTE_URL"
else
    echo "==> Adding remote 'origin' -> $REMOTE_URL"
    git remote add origin "$REMOTE_URL"
fi

# ── Stage and commit ──────────────────────────────────────────────────────────
echo "==> Staging all files..."
git add .

echo "==> Creating initial commit..."
git commit -m "Initial commit — Lloyd's Insight and Syndicate Analyses app"

# ── Push ─────────────────────────────────────────────────────────────────────
echo "==> Pushing to GitHub (branch: main)..."
git push -u origin main

echo ""
echo "================================================================"
echo " Repository pushed successfully."
echo " Remote: $REMOTE_URL"
echo "================================================================"
