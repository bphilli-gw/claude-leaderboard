#!/usr/bin/env bash
# Install git on macOS via Apple's Command Line Tools — no Homebrew, no sudo.
# Triggers Apple's built-in GUI installer (a dialog); nothing to download by hand.
set -euo pipefail

# Command Line Tools (or full Xcode) already present? Then git is already there.
if xcode-select -p >/dev/null 2>&1; then
  echo "Already installed: $(git --version 2>/dev/null || echo 'git (run: git --version)')"
  echo "Nothing to do."
  exit 0
fi

echo "Installing Apple's Command Line Tools — this is what gives you git."
echo "A macOS dialog will pop up: click \"Install\" and wait a few minutes for it to finish."
echo "(It installs in the background, so you can keep going with the other installers.)"
xcode-select --install 2>/dev/null || true

cat <<'EOF'

When the dialog finishes, confirm git works:
  git --version

No dialog appeared? git is probably already installed (run the check above),
or install it from your browser instead: https://git-scm.com/download/mac
EOF
