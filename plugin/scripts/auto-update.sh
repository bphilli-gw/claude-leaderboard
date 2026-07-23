#!/bin/bash
# Push usage totals to the leaderboard at most once per 20h, in the background.
# Must never block or fail a session: every path exits 0 fast.
STATE="$HOME/.claude-leaderboard"
REPO="$STATE/repo"
STAMP="$STATE/last-push"
mkdir -p "$STATE" || exit 0

now=$(date +%s)
last=$(stat -f %m "$STAMP" 2>/dev/null || stat -c %Y "$STAMP" 2>/dev/null || echo 0)
[ $((now - last)) -lt 72000 ] && exit 0
command -v git >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
touch "$STAMP"

nohup bash -c '
  STATE="$HOME/.claude-leaderboard"; REPO="$STATE/repo"
  if [ ! -d "$REPO/.git" ]; then
    gh repo clone bphilli-gw/claude-leaderboard "$REPO" -- --quiet 2>/dev/null \
      || git clone --quiet https://github.com/bphilli-gw/claude-leaderboard.git "$REPO" \
      || exit 0
  fi
  echo "=== $(date) ==="
  python3 "$REPO/collect.py" --push
' >>"$STATE/log" 2>&1 &

exit 0
