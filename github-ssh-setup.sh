#!/usr/bin/env bash
# github-ssh-setup.sh — Generate an SSH key and configure it for GitHub
set -euo pipefail

echo ""
echo "=== GitHub SSH Setup ==="
echo ""

# ── Prompt for GitHub email ───────────────────────────────────────────────────
read -rp "Enter your GitHub email address: " GH_EMAIL
if [[ -z "$GH_EMAIL" ]]; then
    echo "ERROR: Email is required."
    exit 1
fi

KEY_PATH="$HOME/.ssh/id_ed25519_github"

# ── Generate SSH key ──────────────────────────────────────────────────────────
if [ -f "$KEY_PATH" ]; then
    echo ""
    echo "INFO: SSH key already exists at $KEY_PATH"
    read -rp "Generate a new one and overwrite? (y/N): " OVERWRITE
    if [[ "${OVERWRITE,,}" != "y" ]]; then
        echo "Keeping existing key."
    else
        ssh-keygen -t ed25519 -C "$GH_EMAIL" -f "$KEY_PATH" -N ""
        echo "PASS: New SSH key generated."
    fi
else
    echo "==> Generating SSH key..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -C "$GH_EMAIL" -f "$KEY_PATH" -N ""
    echo "PASS: SSH key generated at $KEY_PATH"
fi

# ── Add to ssh-agent ──────────────────────────────────────────────────────────
echo ""
echo "==> Starting ssh-agent and adding key..."
eval "$(ssh-agent -s)"
ssh-add "$KEY_PATH"
echo "PASS: Key added to ssh-agent."

# ── Configure ~/.ssh/config ───────────────────────────────────────────────────
SSH_CONFIG="$HOME/.ssh/config"
if ! grep -q "Host github.com" "$SSH_CONFIG" 2>/dev/null; then
    echo ""
    echo "==> Adding GitHub entry to $SSH_CONFIG..."
    cat >> "$SSH_CONFIG" << EOF

Host github.com
    HostName github.com
    User git
    IdentityFile $KEY_PATH
    IdentitiesOnly yes
EOF
    chmod 600 "$SSH_CONFIG"
    echo "PASS: SSH config updated."
else
    echo "INFO: GitHub entry already exists in $SSH_CONFIG — skipping."
fi

# ── Print public key ──────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo " ACTION REQUIRED — Add this public key to GitHub:"
echo "================================================================"
echo ""
cat "${KEY_PATH}.pub"
echo ""
echo "Steps:"
echo "  1. Copy the key above"
echo "  2. Go to https://github.com/settings/keys"
echo "  3. Click 'New SSH key'"
echo "  4. Paste the key and save"
echo ""

# ── Test connection ───────────────────────────────────────────────────────────
read -rp "Once added, press Enter to test the connection..."
echo ""
echo "==> Testing SSH connection to GitHub..."
if ssh -T git@github.com -o StrictHostKeyChecking=no 2>&1 | grep -q "successfully authenticated"; then
    echo "PASS: SSH connection to GitHub is working."
else
    echo "INFO: GitHub returned the above message — if it says 'successfully authenticated'"
    echo "      then the setup is complete. If not, check that the key was added correctly."
fi

# ── Update repo remote to SSH ─────────────────────────────────────────────────
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ -d ".git" ]; then
    CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ "$CURRENT_REMOTE" == https://* ]]; then
        echo ""
        read -rp "Current remote uses HTTPS. Enter your GitHub username to switch to SSH: " GH_USER
        REPO_NAME=$(basename "$CURRENT_REMOTE" .git)
        NEW_REMOTE="git@github.com:${GH_USER}/${REPO_NAME}.git"
        git remote set-url origin "$NEW_REMOTE"
        echo "PASS: Remote updated to $NEW_REMOTE"
    elif [[ "$CURRENT_REMOTE" == git@* ]]; then
        echo "INFO: Remote is already using SSH: $CURRENT_REMOTE"
    fi
fi

echo ""
echo "================================================================"
echo " SSH setup complete."
echo "================================================================"
