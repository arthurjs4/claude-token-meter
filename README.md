# claude-token-meter

A tiny, dependency-free CLI that tells you how many tokens a Claude Code session and its subagents used, split into new input, cache created, cache read and output.

## Why

Long Claude Code sessions re-read a large base context on every response, so most of the "reading" is cache. Looking only at output tokens hides where the usage went. This tool reads the logs Claude Code already writes locally and gives you a markdown table per session and per agent type, so you can see which workflow or subagent is expensive.

## Install

```bash
pip install .          # Python 3.9+; no third-party dependencies
```

Or run it without installing: `PYTHONPATH=src python -m claude_token_meter.cli`.

## Usage

```bash
claude-token-meter                              # most recent session of any project
claude-token-meter --project /path/to/project   # most recent session of one project
claude-token-meter --session <id>               # a specific session (the .jsonl name)
claude-token-meter --since 2026-01-31T09:30:00  # only what happened after a local time
claude-token-meter --append-to notes.md         # also append a "## Token usage" section to a file
```

Logs are read from `~/.claude/projects/<project-folder>/<session>.jsonl` and `<session>/subagents/agent-*.jsonl` (override the root with `--projects-dir`). Nothing is modified.

## Example output

```
Session: 0b1f6c2e-demo (whole session)

| Part | Responses | New input | Cache created | Cache read | Output |
|---|---|---|---|---|---|
| session (main) | 42 | 310 | 58,200 | 1,904,500 | 21,340 |
| agent researcher (3x) | 55 | 120 | 91,400 | 2,310,000 | 18,900 |
| **Total** | 97 | 430 | 149,600 | 4,214,500 | 40,240 |

Read: 4,364,530 tokens (97% re-read from cache) | written: 40,240 tokens
```

Subagents of the same type are grouped (`3x` = three runs). The numbers above are made up.

## Tests

```bash
pip install pytest && pytest
```

## Limitations

- The log format is an internal detail of Claude Code and may change; the tool skips lines it cannot parse.
- It counts tokens, not money or plan limits.
- Responses repeated in the log (same request id) are counted once. The project-folder naming rule is a best-effort mirror of Claude Code's; use `--session` if `--project` does not find your logs.

## License

MIT

## Resumo em português

CLI sem dependências que lê os logs locais do Claude Code e mostra, em tabela markdown, os tokens de uma sessão e dos subagentes: entrada nova, cache criado, cache lido e saída. Serve para descobrir qual fluxo ou agente gasta mais. Só lê, nunca altera nada. Limitação: o formato dos logs pode mudar.
