#!/usr/bin/env bash
# Install the GitHub CLI (gh) on macOS — no Homebrew, no sudo, no Gatekeeper hassle.
# Downloads the prebuilt binary into ~/.local/bin using only system tools (curl, unzip).
set -euo pipefail

case "$(uname -m)" in
  arm64)  arch="arm64" ;;
  x86_64) arch="amd64" ;;
  *) echo "Unsupported architecture: $(uname -m). Install manually from https://github.com/cli/cli/releases"; exit 1 ;;
esac

echo "Finding the latest gh release..."
ver="$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest \
  | sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p')"
if [ -z "${ver:-}" ]; then
  echo "Couldn't read the latest gh version. Install manually from https://github.com/cli/cli/releases"; exit 1
fi

asset="gh_${ver}_macOS_${arch}.zip"
url="https://github.com/cli/cli/releases/download/v${ver}/${asset}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading gh ${ver} (${asset})..."
curl -fSL "$url" -o "$tmp/gh.zip"
unzip -q "$tmp/gh.zip" -d "$tmp"

ghbin="$(find "$tmp" -type f -path '*/bin/gh' | head -1)"
if [ -z "${ghbin:-}" ]; then
  echo "Couldn't find the gh binary in the download. Install manually from https://github.com/cli/cli/releases"; exit 1
fi

mkdir -p "$HOME/.local/bin"
mv "$ghbin" "$HOME/.local/bin/gh"
chmod +x "$HOME/.local/bin/gh"
xattr -d com.apple.quarantine "$HOME/.local/bin/gh" 2>/dev/null || true   # clear macOS Gatekeeper flag

# Make sure ~/.local/bin is on PATH for future shells
if ! grep -qs '\.local/bin' "$HOME/.zshrc" 2>/dev/null; then
  printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.zshrc"
fi
export PATH="$HOME/.local/bin:$PATH"

echo
echo "Installed: $("$HOME/.local/bin/gh" --version 2>/dev/null | head -1)"
echo "Done. If 'gh' isn't found in a new terminal, run: source ~/.zshrc"
