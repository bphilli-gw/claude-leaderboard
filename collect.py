#!/usr/bin/env python3
"""Aggregate your local Claude Code usage logs into daily totals.

Reads ~/.claude/projects/**/*.jsonl, dedupes streamed messages, and writes
data/<github-username>.json containing ONLY daily aggregates: token counts
by model, and session counts. No prompts, code, file paths, or conversation
content ever leave your machine.

Usage:
    python3 collect.py            # write your data file
    python3 collect.py --push     # also rebuild dashboard.html, commit, push

Stdlib only. Requires `gh` (for your GitHub username) or pass --user.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_PROJECTS = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"
REPO_ROOT = Path(__file__).resolve().parent


def github_username():
    try:
        out = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def collect():
    """Return {date: {"models": {model: {in,out,cc,cr}}, "sessions": set()}}."""
    # Streaming writes the same message id several times; last write wins.
    # Key on (message id, request id) so retries of a request don't double-count.
    messages = {}
    if not CLAUDE_PROJECTS.is_dir():
        sys.exit(f"No Claude Code logs found at {CLAUDE_PROJECTS}")
    for path in CLAUDE_PROJECTS.rglob("*.jsonl"):
        try:
            with open(path, errors="replace") as fh:
                for line in fh:
                    if '"usage"' not in line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") != "assistant":
                        continue
                    msg = entry.get("message") or {}
                    usage = msg.get("usage")
                    if not usage or not msg.get("model") or msg.get("model") == "<synthetic>":
                        continue
                    key = (msg.get("id"), entry.get("requestId"))
                    messages[key] = {
                        "ts": entry.get("timestamp"),
                        "session": entry.get("sessionId"),
                        "model": msg["model"],
                        "in": usage.get("input_tokens", 0),
                        "out": usage.get("output_tokens", 0),
                        "cc": usage.get("cache_creation_input_tokens", 0),
                        "cr": usage.get("cache_read_input_tokens", 0),
                    }
        except OSError:
            continue

    days = defaultdict(lambda: {"models": defaultdict(lambda: {"in": 0, "out": 0, "cc": 0, "cr": 0}),
                                "sessions": set()})
    for m in messages.values():
        if not m["ts"]:
            continue
        try:
            ts = datetime.fromisoformat(m["ts"].replace("Z", "+00:00"))
        except ValueError:
            continue
        day = ts.replace(tzinfo=ts.tzinfo or timezone.utc).astimezone().date().isoformat()
        rec = days[day]
        model = rec["models"][m["model"]]
        for k in ("in", "out", "cc", "cr"):
            model[k] += m[k]
        if m["session"]:
            rec["sessions"].add(m["session"])
    return days


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", help="username for your data file (default: gh api user)")
    ap.add_argument("--push", action="store_true", help="rebuild dashboard, commit, and push")
    args = ap.parse_args()

    user = args.user or github_username()
    if not user:
        sys.exit("Couldn't get your GitHub username from `gh`. Pass --user <name>.")

    days = collect()
    out = {
        "user": user,
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": {
            day: {
                "sessions": len(rec["sessions"]),
                "models": {model: dict(t) for model, t in sorted(rec["models"].items())},
            }
            for day, rec in sorted(days.items())
        },
    }
    dest = REPO_ROOT / "data" / f"{user}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=1) + "\n")

    total = sum(t[k] for rec in days.values() for t in rec["models"].values() for k in ("in", "out", "cc", "cr"))
    print(f"Wrote {dest.relative_to(REPO_ROOT)}: {len(days)} active days, {total:,} total tokens")

    if args.push:
        subprocess.run([sys.executable, str(REPO_ROOT / "build.py")], check=True)
        subprocess.run(["git", "-C", str(REPO_ROOT), "pull", "--rebase", "--quiet"], check=True)
        subprocess.run(["git", "-C", str(REPO_ROOT), "add", "data", "dashboard.html"], check=True)
        diff = subprocess.run(["git", "-C", str(REPO_ROOT), "diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            print("No changes to push.")
            return
        subprocess.run(["git", "-C", str(REPO_ROOT), "commit", "--quiet",
                        "-m", f"Update {user} usage data"], check=True)
        subprocess.run(["git", "-C", str(REPO_ROOT), "push", "--quiet"], check=True)
        print("Pushed.")


if __name__ == "__main__":
    main()
