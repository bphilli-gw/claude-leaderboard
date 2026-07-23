# Claude Leaderboard

An opt-in, straude-style leaderboard for Claude Code usage at GiveWell. Daily token totals, streaks, and a dashboard. Tokens are volume, not value; this is for fun and bragging rights, not performance measurement.

## What leaves your machine

Only daily aggregates: token counts by model, and session counts per day. The collector reads your local Claude Code logs (`~/.claude/projects`), sums them up, and writes one small JSON file to `data/<your-github-username>.json` in this repo. Prompts, code, conversation content, project names, and file paths never leave your machine. Read `collect.py` (about 100 lines, stdlib only) to verify.

Two known gaps: Cowork usage isn't counted (it doesn't write these local logs), and history only goes back as far as your local logs do (Claude Code prunes old sessions).

## Join in

You need Python 3 and the `gh` CLI (which you have if you set up GitHub via the givewell-gws-setup installers).

```bash
git clone https://github.com/bphilli-gw/claude-leaderboard.git
cd claude-leaderboard
python3 collect.py --push
```

That's it. Run `python3 collect.py --push` again whenever you want to update your numbers (end of day works well). To automate it, add a daily launchd/cron job, or ask Claude Code to set one up for you.

## View the dashboard

```bash
git pull && open dashboard.html
```

`dashboard.html` is rebuilt and committed on every `--push`, so it always reflects the latest data in the repo.

## How the numbers are computed

- **Tokens** = input + output + cache creation + cache reads (everything Claude processed for you). Cache reads dominate; that's normal for agentic sessions.
- **Output** = tokens Claude generated, shown separately as the "real work" number.
- **Sessions** = distinct Claude Code sessions with at least one response that day.
- **Streak** = consecutive calendar days with any usage, ending today or yesterday. Weekends count against you. Git blame the scoreboard, not the referee.
