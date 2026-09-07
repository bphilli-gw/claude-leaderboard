# Claude Leaderboard — ABSOLUTE GRINDSET EDITION

An opt-in, straude-style leaderboard for Claude Code and Codex CLI usage at GiveWell. Daily token totals, streaks, and a dashboard. Tokens are volume, not value; this is for fun and bragging rights, not performance measurement.

## What leaves your machine

Only daily aggregates: token counts by model, and session counts per day. The collector reads your local Claude Code logs (`~/.claude/projects`) and Codex CLI logs (`~/.codex/sessions`), sums them up, and writes one small JSON file to `data/<your-github-username>.json` in this repo. Prompts, code, conversation content, project names, and file paths never leave your machine. Read `collect.py` (about 250 lines, stdlib only) to verify.

Two known gaps: Cowork usage isn't counted (it doesn't write these local logs), and history only goes back as far as your local logs do (Claude Code prunes old sessions). Codex rollouts written by CLI 0.147 or earlier have no per-response usage records, so those days use Codex's coarser per-turn counter (within a couple of percent).

**This repo is public** so the dashboard can live on GitHub Pages. Joining means your GitHub handle and daily token totals are visible on the open internet. If you're not comfortable with that, don't join (or ask Brendan about a pseudonym).

## Join in (the plugin way — recommended)

In Claude Code:

```
/plugin marketplace add bphilli-gw/claude-leaderboard
/plugin install claude-leaderboard@claude-leaderboard
```

Restart Claude Code, then run `/leaderboard` and say you want to join. It handles setup and your first push, and from then on the plugin auto-pushes your daily totals (at most once a day, silently, when a session ends). You never think about it again. The grind simply accrues.

You'll also need push access: send Brendan your GitHub handle on Slack.

**Missing git or the `gh` CLI?** Run the installers in [`setup/`](setup/) — no Homebrew, no sudo:

```bash
bash setup/install-git.sh   # Apple's Command Line Tools dialog; skips if present
bash setup/install-gh.sh    # gh into ~/.local/bin
gh auth login               # pick GitHub.com → HTTPS → login with browser
```

## Join in (the manual way)

```bash
git clone https://github.com/bphilli-gw/claude-leaderboard.git
cd claude-leaderboard
python3 collect.py --push
```

Run `python3 collect.py --push` again whenever you want to update your numbers.

## View the dashboard

Live at **https://bphilli-gw.github.io/claude-leaderboard/** (updates a minute or so after each push). Or locally: `git pull && open index.html`. `index.html` is rebuilt and committed on every `--push`.

## How the numbers are computed

- **Tokens** = input + output + cache creation + cache reads (everything the machine processed for you). Cache reads dominate; that's normal for agentic sessions.
- **Codex counts too.** Codex models appear as `codex/<model>` in the data files, and the Armory table on the dashboard breaks tokens down by machine and gladiator. OpenAI reports cached input inside its input count; the collector splits it back out so cache reads line up with Claude's.
- **Output** = tokens the model generated, shown separately as the "real work" number.
- **Sessions** = distinct Claude Code sessions plus distinct Codex threads (a Codex thread and its sub-agents count once) with at least one response that day.
- **Streak** = consecutive days with any usage, ending today or yesterday. Weekends can't break you: an idle Saturday or Sunday is skipped, and weekend usage still counts. Only an idle weekday ends the grind. Git blame the scoreboard, not the referee.
