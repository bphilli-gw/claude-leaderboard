#!/usr/bin/env python3
"""Aggregate your local Claude Code and Codex CLI usage logs into daily totals.

Reads ~/.claude/projects/**/*.jsonl and ~/.codex/sessions/**/*.jsonl, dedupes
streamed/retried messages, and writes data/<github-username>.json containing
ONLY daily aggregates: token counts by model, and session counts. No prompts,
code, file paths, or conversation content ever leave your machine.

Local logs are not forever (Claude Code deletes a transcript 30 days after its
last activity), so each run folds the already-published days back in: per day
and model the larger count wins, and days the logs no longer contain are kept
as published. Pass --fresh to rebuild from local logs alone.

Claude models keep their bare names; Codex models are keyed "codex/<model>" so
the dashboard can tell the two machines apart. Both count toward every total.

Usage:
    python3 collect.py            # write your data file
    python3 collect.py --push     # also rebuild index.html, commit, push
    python3 collect.py --fresh    # ignore the published file (drops history)

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
CODEX_SESSIONS = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
REPO_ROOT = Path(__file__).resolve().parent

# The arena runs on Pacific time: everyone's day buckets flip at midnight PT,
# whatever timezone their machine is in. Falls back to machine-local if the
# tz database is missing — never let this crash a session-end hook.
try:
    from zoneinfo import ZoneInfo
    ARENA_TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    ARENA_TZ = None


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


def claude_responses():
    """One record per Claude Code API response: {ts, session, model, in, out, cc, cr}."""
    # Streaming writes the same message id several times; last write wins.
    # Key on (message id, request id) so retries of a request don't double-count.
    messages = {}
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
    return list(messages.values())


def codex_usage(u):
    """Map OpenAI usage fields onto ours. OpenAI's input_tokens INCLUDES cached
    tokens (Anthropic's excludes them), so uncached input = input - cached."""
    cached = u.get("cached_input_tokens", 0)
    return {"in": max(u.get("input_tokens", 0) - cached, 0), "out": u.get("output_tokens", 0),
            "cc": u.get("cache_write_input_tokens", 0), "cr": cached}


def codex_responses():
    """One record per Codex API response, same shape as claude_responses().

    Codex writes one rollout file per thread. Each API response appends a
    token_usage_record keyed by response_id; the model lives on the turn_context
    of the same turn. Sub-agent threads get their own file but name their parent,
    so a parent and its sub-agents count as one session. Rollouts from Codex CLI
    0.147 and earlier have no token_usage_record; for those we fall back to the
    per-turn token_count events (within ~2% of the real figure).
    """
    responses, parent, fallback = {}, {}, []
    for path in CODEX_SESSIONS.rglob("*.jsonl"):
        turn_model, model, thread, old_style, prev = {}, None, None, [], None
        try:
            with open(path, errors="replace") as fh:
                for line in fh:
                    if not any(k in line for k in ('"token_usage_record"', '"turn_context"', '"session_meta"', '"token_count"')):
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    kind, p = entry.get("type"), entry.get("payload") or {}
                    if kind == "session_meta":
                        thread = p.get("id")
                        src = p.get("thread_source")
                        spawn = src.get("subagent", {}).get("thread_spawn", {}) if isinstance(src, dict) else {}
                        parent[thread] = spawn.get("parent_thread_id") or thread
                    elif kind == "turn_context":
                        model = p.get("model") or model
                        turn_model[p.get("turn_id")] = model
                    elif kind == "token_usage_record":
                        key = p.get("response_id") or (path.name, entry.get("ordinal"))
                        responses[key] = {
                            "ts": entry.get("timestamp"),
                            "session": p.get("session_id") or thread,
                            "model": "codex/" + (turn_model.get(p.get("turn_id")) or model or "unknown"),
                            **codex_usage(p.get("usage") or {}),
                        }
                    elif kind == "event_msg" and p.get("type") == "token_count":
                        last = (p.get("info") or {}).get("last_token_usage")
                        if last and last != prev:  # repeated events for the same response
                            old_style.append({"ts": entry.get("timestamp"), "session": thread,
                                              "model": "codex/" + (model or "unknown"), **codex_usage(last)})
                        prev = last
        except OSError:
            continue
        if old_style and not any(r["session"] == thread for r in responses.values()):
            fallback.extend(old_style)
    out = list(responses.values()) + fallback
    for r in out:
        r["session"] = parent.get(r["session"], r["session"])
    return out


def collect():
    """Return {date: {"models": {model: {in,out,cc,cr}}, "sessions": set()}}."""
    sources = [(CLAUDE_PROJECTS, claude_responses), (CODEX_SESSIONS, codex_responses)]
    if not any(d.is_dir() for d, _ in sources):
        sys.exit(f"No Claude Code logs at {CLAUDE_PROJECTS} and no Codex logs at {CODEX_SESSIONS}")
    records = [r for d, read in sources if d.is_dir() for r in read()]

    days = defaultdict(lambda: {"models": defaultdict(lambda: {"in": 0, "out": 0, "cc": 0, "cr": 0}),
                                "sessions": set()})
    for m in records:
        if not m["ts"]:
            continue
        try:
            ts = datetime.fromisoformat(m["ts"].replace("Z", "+00:00"))
        except ValueError:
            continue
        day = ts.replace(tzinfo=ts.tzinfo or timezone.utc).astimezone(ARENA_TZ).date().isoformat()
        rec = days[day]
        model = rec["models"][m["model"]]
        for k in ("in", "out", "cc", "cr"):
            model[k] += m[k]
        if m["session"]:
            rec["sessions"].add(m["session"])
    return days


def published_days(dest):
    """Days already committed for this user, read from HEAD rather than the
    working tree so a dirty or conflicted file can't feed garbage into the merge.
    {} for a new user (no file yet) or anything unreadable."""
    rel = dest.relative_to(REPO_ROOT).as_posix()
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"HEAD:{rel}"],
                             capture_output=True, text=True, timeout=15)
        if out.returncode == 0:
            return json.loads(out.stdout).get("days") or {}
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError):
        pass
    return {}


def merge_history(fresh, published):
    """Fold the published days back into the freshly collected ones.

    Claude Code deletes a session's transcript 30 days after its last activity
    (`cleanupPeriodDays`), so a fresh collect() sees less of a month-old day on
    every run: the short sessions drop out first and the day shrinks, then it
    vanishes. Nothing legitimate makes a day's count go DOWN between runs, so per
    day and model we keep the larger of fresh vs published, and days the logs no
    longer know about are carried forward as they were. Both inputs are in the
    data-file shape: {day: {"sessions": n, "models": {model: {in,out,cc,cr}}}}.
    Returns (merged, carried) — carried is how many days exist only as published.
    """
    merged, carried = {}, 0
    for day in sorted(set(fresh) | set(published)):
        new, old = fresh.get(day), published.get(day) or {}
        if new is None:
            merged[day] = old
            carried += 1
            continue
        models = {model: dict(t) for model, t in new["models"].items()}
        for model, t in (old.get("models") or {}).items():
            cur = models.setdefault(model, {"in": 0, "out": 0, "cc": 0, "cr": 0})
            for k in ("in", "out", "cc", "cr"):
                cur[k] = max(cur.get(k, 0), t.get(k, 0))
        merged[day] = {
            "sessions": max(new["sessions"], old.get("sessions", 0)),
            "models": dict(sorted(models.items())),
        }
    return merged, carried


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", help="username for your data file (default: gh api user)")
    ap.add_argument("--push", action="store_true", help="rebuild dashboard, commit, and push")
    ap.add_argument("--fresh", action="store_true",
                    help="don't merge with the published file; write only what local logs contain (drops history)")
    args = ap.parse_args()

    user = args.user or github_username()
    if not user:
        sys.exit("Couldn't get your GitHub username from `gh`. Pass --user <name>.")

    git = ["git", "-C", str(REPO_ROOT)]
    if args.push:
        # Pull before collecting so the merge below sees the latest published file.
        subprocess.run(git + ["pull", "--rebase", "--autostash", "--quiet"], check=True)

    dest = REPO_ROOT / "data" / f"{user}.json"
    days = collect()
    fresh = {
        day: {
            "sessions": len(rec["sessions"]),
            "models": {model: dict(t) for model, t in sorted(rec["models"].items())},
        }
        for day, rec in sorted(days.items())
    }
    merged, carried = (fresh, 0) if args.fresh else merge_history(fresh, published_days(dest))
    out = {
        "user": user,
        "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": merged,
    }
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=1) + "\n")

    by_tool = defaultdict(int)
    for rec in merged.values():
        for model, t in rec["models"].items():
            by_tool["codex" if model.startswith("codex/") else "claude"] += sum(t.values())
    total = sum(by_tool.values())
    split = f" ({by_tool['codex']:,} via Codex)" if by_tool["codex"] else ""
    kept = f" ({carried} carried from published history)" if carried else ""
    print(f"Wrote {dest.relative_to(REPO_ROOT)}: {len(merged)} active days{kept}, {total:,} total tokens{split}")

    if args.push:
        # Only data/ is committed; the dashboard is rebuilt by the Pages workflow,
        # so concurrent pushers can never conflict (each touches only their own file).
        subprocess.run([sys.executable, str(REPO_ROOT / "build.py")], check=True)  # local convenience copy
        ident = subprocess.run(git + ["config", "user.email"], capture_output=True, text=True)
        if not ident.stdout.strip():
            subprocess.run(git + ["config", "user.name", user], check=True)
            subprocess.run(git + ["config", "user.email", f"{user}@users.noreply.github.com"], check=True)
        # We pulled before writing, so `--autostash` only ever stashes other
        # people's local edits — and if re-applying one leaves conflict markers in
        # our file, the write above already replaced it wholesale from `out`
        # (built from HEAD, never from the working tree). Never stage anything else.
        subprocess.run(git + ["add", str(dest)], check=True)
        try:
            json.loads(dest.read_text())
        except json.JSONDecodeError as e:
            sys.exit(f"Refusing to push malformed {dest.name}: {e}")
        diff = subprocess.run(git + ["diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            print("No changes to push.")
            return
        subprocess.run(git + ["commit", "--quiet", "-m", f"Update {user} usage data"], check=True)
        for attempt in (1, 2, 3):
            if subprocess.run(git + ["push", "--quiet"]).returncode == 0:
                print("Pushed.")
                return
            subprocess.run(git + ["pull", "--rebase", "--autostash", "--quiet"], check=True)
        sys.exit("Push failed after retries. If it's a 403, ask Brendan for push access.")


if __name__ == "__main__":
    main()
