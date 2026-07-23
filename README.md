# Claude Leaderboard

An opt-in, straude-style leaderboard for Claude Code usage at GiveWell. Daily token totals, streaks, and a dashboard. Tokens are volume, not value; this is for fun and bragging rights, not performance measurement.

## What leaves your machine

Only daily aggregates: token counts by model, and session counts per day. The collector reads your local Claude Code logs (`~/.claude/projects`), sums them up, and writes one small JSON file to `data/<your-github-username>.json` in this repo. Prompts, code, conversation content, project names, and file paths never leave your machine. Read `collect.py` (about 100 lines, stdlib only) to verify.

Two known gaps: Cowork usage isn't counted (it doesn't write these local logs), and history only goes back as far as your local logs do (Claude Code prunes old sessions).

**This repo is public** so the dashboard can live on GitHub Pages. Joining means your GitHub handle and daily token totals are visible on the open internet. If you're not comfortable with that, don't join (or ask Brendan about a pseudonym).

## Join in

You need Python 3 and the `gh` CLI (most GiveWell staff already have both from the GitHub setup).

```bash
git clone https://github.com/bphilli-gw/claude-leaderboard.git
cd claude-leaderboard
python3 collect.py --push
```

That's it. Run `python3 collect.py --push` again whenever you want to update your numbers (end of day works well). To automate it, add a daily launchd/cron job, or ask Claude Code to set one up for you.

## View the dashboard

Live at **https://bphilli-gw.github.io/claude-leaderboard/** (updates a minute or so after each push). Or locally: `git pull && open index.html`. `index.html` is rebuilt and committed on every `--push`.

## How the numbers are computed

- **Tokens** = input + output + cache creation + cache reads (everything Claude processed for you). Cache reads dominate; that's normal for agentic sessions.
- **Output** = tokens Claude generated, shown separately as the "real work" number.
- **Sessions** = distinct Claude Code sessions with at least one response that day.
- **Streak** = consecutive calendar days with any usage, ending today or yesterday. Weekends count against you. Git blame the scoreboard, not the referee.
