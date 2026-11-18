"""Sum the tokens a Claude Code session (and its subagents) used, from the local JSONL logs.

Read-only: it never changes anything. Logs live in ~/.claude/projects/<project-folder>/<session>.jsonl and subagent
logs in <session>/subagents/agent-*.jsonl (the `usage` field of every assistant response).

Categories:
  new input     text the model read for the first time
  cache created text stored so it can be re-read cheaply
  cache read    text re-read from the cache (weighs much less on plan limits)
  output        what the model wrote (includes reasoning)
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

CATEGORIES = ("input", "cache_created", "cache_read", "output")


def project_dir_name(path):
    """Claude Code names the log folder after the project path, with separators replaced by dashes."""
    return str(path).replace(":", "-").replace("\\", "-").replace("/", "-")


def sum_usage(jsonl, since=None):
    """Return totals for one JSONL file. Duplicated responses (same request id) are counted once."""
    t = {"input": 0, "cache_created": 0, "cache_read": 0, "output": 0, "responses": 0}
    seen = set()
    with open(jsonl, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") or {}
            u = msg.get("usage")
            if not u or d.get("type") != "assistant":
                continue
            key = d.get("requestId") or msg.get("id") or d.get("uuid")
            if key in seen:
                continue
            seen.add(key)
            if since and d.get("timestamp"):
                ts = datetime.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                if ts < since:
                    continue
            t["input"] += u.get("input_tokens") or 0
            t["cache_created"] += u.get("cache_creation_input_tokens") or 0
            t["cache_read"] += u.get("cache_read_input_tokens") or 0
            t["output"] += u.get("output_tokens") or 0
            t["responses"] += 1
    return t


def agent_label(path):
    meta = path.with_suffix(".meta.json")
    if meta.exists():
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            return m.get("agentType") or m.get("subagent_type") or m.get("description") or path.stem
        except ValueError:
            pass
    return path.stem


def collect(session_file, since=None):
    """List of (label, totals): the main session first, then each subagent grouped by type."""
    parts = [("session (main)", sum_usage(session_file, since))]
    sub = session_file.with_suffix("") / "subagents"
    if sub.exists():
        for f in sorted(sub.glob("agent-*.jsonl")):
            t = sum_usage(f, since)
            if t["responses"]:
                parts.append((f"agent {agent_label(f)}", t))
    grouped = {}
    for label, t in parts:
        g = grouped.setdefault(label, {k: 0 for k in t})
        g["runs"] = g.get("runs", 0) + 1
        for k, v in t.items():
            g[k] += v
    return list(grouped.items())


def fmt(n):
    return f"{n:,}"


def to_markdown(session_id, rows, since=None):
    total = {k: sum(g[k] for _, g in rows) for k in (*CATEGORIES, "responses")}
    head = f"Session: {session_id}" + (f" (since {since:%Y-%m-%d %H:%M})" if since else " (whole session)")
    out = [head, "", "| Part | Responses | New input | Cache created | Cache read | Output |", "|---|---|---|---|---|---|"]
    for label, g in rows:
        name = label + (f" ({g['runs']}x)" if g["runs"] > 1 else "")
        out.append(f"| {name} | {g['responses']} | {fmt(g['input'])} | {fmt(g['cache_created'])} | "
                   f"{fmt(g['cache_read'])} | {fmt(g['output'])} |")
    out.append(f"| **Total** | {total['responses']} | {fmt(total['input'])} | {fmt(total['cache_created'])} | "
               f"{fmt(total['cache_read'])} | {fmt(total['output'])} |")
    read = total["input"] + total["cache_created"] + total["cache_read"]
    out.append("")
    if read:
        out.append(f"Read: {fmt(read)} tokens ({100 * total['cache_read'] / read:.0f}% re-read from cache) | "
                   f"written: {fmt(total['output'])} tokens")
    else:
        out.append("No usage recorded in this interval.")
    return "\n".join(out)


def find_session(projects_root, project, session):
    if project:
        folder = projects_root / project_dir_name(pathlib.Path(project).resolve())
        if not folder.exists():
            sys.exit(f"no logs found for that project at {folder}")
        folders = [folder]
    else:
        folders = [p for p in projects_root.iterdir() if p.is_dir()] if projects_root.exists() else []
    if session:
        for f in folders:
            cand = f / f"{session}.jsonl"
            if cand.exists():
                return cand
        sys.exit(f"session not found: {session}")
    files = [p for f in folders for p in f.glob("*.jsonl")]
    if not files:
        sys.exit(f"no sessions found under {projects_root}")
    return max(files, key=lambda p: p.stat().st_mtime)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Token usage of a Claude Code session and its subagents.")
    ap.add_argument("--projects-dir", default=os.path.join(os.path.expanduser("~"), ".claude", "projects"),
                    help="root of the Claude Code logs (default: ~/.claude/projects)")
    ap.add_argument("--project", help="project folder whose sessions to look at (default: all projects)")
    ap.add_argument("--session", help="session id (the .jsonl name); default: the most recently modified")
    ap.add_argument("--since", help="count only after this local time, e.g. 2026-01-31T09:30:00")
    ap.add_argument("--append-to", help="append a '## Token usage' section to this markdown file")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    since = None
    if a.since:
        since = datetime.datetime.fromisoformat(a.since)
        if since.tzinfo is None:
            since = since.astimezone()
    session = find_session(pathlib.Path(a.projects_dir), a.project, a.session)
    text = to_markdown(session.stem, collect(session, since), since)
    print(text)
    if a.append_to:
        with open(a.append_to, "a", encoding="utf-8") as fh:
            fh.write("\n\n## Token usage\n\n" + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
