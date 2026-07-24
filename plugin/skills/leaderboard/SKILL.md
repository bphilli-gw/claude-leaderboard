---
name: leaderboard
description: Join or update the GiveWell Claude Leaderboard (ABSOLUTE GRINDSET EDITION). Use when the user wants to join the leaderboard, push or update their Claude Code usage numbers, check their rank or streak, or troubleshoot leaderboard updates ("join the leaderboard", "update my numbers", "what's my streak", "why isn't my usage showing").
---

# GiveWell Claude Leaderboard

Opt-in token-usage leaderboard: https://bphilli-gw.github.io/claude-leaderboard/
Maintainer: Brendan Phillips (`bphilli-gw` on GitHub, @Brendan Phillips on Slack).

The repo is PUBLIC. Joining publishes the user's GitHub handle and daily token totals
(nothing else — no prompts, code, or content) on the open internet. On first join,
say this in one sentence and confirm they're in before pushing.

## Setup / join (first run)

1. Check auth: `gh auth status`. If not logged in, walk them through `gh auth login`.
2. Clone if missing (this exact path — the auto-update hook uses it too):
   `gh repo clone bphilli-gw/claude-leaderboard "$HOME/.claude-leaderboard/repo"`
3. Push their numbers: `python3 "$HOME/.claude-leaderboard/repo/collect.py" --push`
4. On success, tell them: their totals, the dashboard URL (updates ~1 min after push),
   and that the plugin now auto-pushes at most once a day when a Claude Code session ends —
   nothing else to do. Their history starts from however far back their local logs go.

## Update / status

- Manual update: `python3 "$HOME/.claude-leaderboard/repo/collect.py" --push`
- Rank/streak questions: read `$HOME/.claude-leaderboard/repo/data/*.json` after a
  `git -C "$HOME/.claude-leaderboard/repo" pull`, compute, and answer. Streak rule:
  consecutive days with usage; idle weekends are skipped (never break a streak);
  only an idle weekday breaks it.

## Troubleshooting

- **Push rejected (403 / permission denied)**: they need push access — tell them to
  send Brendan their GitHub handle on Slack. Everything else can wait; the commit
  is preserved locally and the next `--push` will deliver it.
- **Their row isn't on the site**: the dashboard rebuilds via GitHub Actions on each
  push (~1 min). Check `git -C "$HOME/.claude-leaderboard/repo" log --oneline -3` to
  confirm their commit exists, then check the Actions tab on the repo.
- **Auto-update didn't run**: it's throttled to once per 2h and logs to
  `$HOME/.claude-leaderboard/log`. Read that file.
- **No usage found**: Claude Code logs live in `~/.claude/projects`. Cowork usage is
  not counted (no local logs) — that's a known gap, not a bug.
