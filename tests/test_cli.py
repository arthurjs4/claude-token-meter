import json

from claude_token_meter import cli


def line(rid, i, cc, cr, o, ts="2026-01-01T10:00:00Z"):
    return json.dumps({"type": "assistant", "requestId": rid, "timestamp": ts,
                       "message": {"usage": {"input_tokens": i, "cache_creation_input_tokens": cc,
                                             "cache_read_input_tokens": cr, "output_tokens": o}}})


def make(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    s = proj / "abc.jsonl"
    s.write_text("\n".join([line("r1", 10, 100, 1000, 5), line("r1", 10, 100, 1000, 5), line("r2", 1, 0, 50, 7)]))
    sub = proj / "abc" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-1.jsonl").write_text(line("a1", 2, 20, 200, 9))
    (sub / "agent-1.meta.json").write_text(json.dumps({"agentType": "researcher"}))
    return tmp_path, s


def test_dedup_and_totals(tmp_path):
    _, s = make(tmp_path)
    t = cli.sum_usage(s)
    assert t == {"input": 11, "cache_created": 100, "cache_read": 1050, "output": 12, "responses": 2}


def test_agents_grouped(tmp_path):
    _, s = make(tmp_path)
    rows = dict(cli.collect(s))
    assert rows["agent researcher"]["output"] == 9
    md = cli.to_markdown("abc", list(rows.items()))
    assert "| **Total** | 3 |" in md


def test_find_latest(tmp_path):
    root, s = make(tmp_path)
    assert cli.find_session(root, None, None) == s
