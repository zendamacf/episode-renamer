# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Humans: [CONTRIBUTING.md](CONTRIBUTING.md).

## Project

CLI that renames TV episodes via TMDB and sorts them under `MOVED`. Config: `config.json` (`config-example.json`).

## Layout

| Module | Role |
| --- | --- |
| `run.py` | CLI, config, rename / undo / history |
| `file_io.py` | Config validation, parsing, rename/move, recursive scan |
| `moviedb.py` | TMDB client, paginated search, sanitized errors |
| `series_cache.py` | Cached series picks (`series_cache.json`) |
| `history.py` | Undo batches (`rename_history.json`) |
| `log.py` | Logging, `--quiet`, summary |
| `tests/` | `test_*.py` beside root modules (no package subfolder) |

## Setup and verification

Use [CONTRIBUTING.md § Python and environment](CONTRIBUTING.md#python-and-environment), then **`make ci`**.

If `python` is missing on PATH, use `python3` and `python3 -m` for pytest/Ruff/basedpyright. CI runs on **3.12** and **3.14**; **3.12+** locally is enough.

## Checklist

1. Smallest correct diff; follow [code style](CONTRIBUTING.md#code-style).
2. Behavior changes → tests; [coverage ≥ 95%](CONTRIBUTING.md#test-coverage).
3. [Changelog fragment](RELEASE.md#during-development) when user-facing or release-noted.
4. Update [README.md](README.md) for CLI flags, config keys, or user-visible behavior.
5. PR body: one `Fixes #N` line per issue (not combined).

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/) for every commit and PR title: `type(scope): short imperative summary`.
- Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`. Scope is optional, for example `fix(moviedb): handle empty search results`.
- Keep the subject under about 72 characters. The PR number is added at the end on merge, for example `(#90)`.
- Release commits use `chore: release X.Y.Z`. Older history does not follow this format, but new commits must.

## Rules

- Mock TMDB in tests; never commit real API keys.
- Do not overwrite or delete user media on ambiguous paths; follow existing `rename_and_move` skip/log behavior.

Do not bump version or run `make release` unless the task asks; see [RELEASE.md](RELEASE.md).
