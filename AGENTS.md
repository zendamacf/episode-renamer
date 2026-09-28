# Agent guide

Instructions for automated coding agents (Cursor, Copilot, etc.) working in this repository. Human contributors should use [CONTRIBUTING.md](CONTRIBUTING.md).

## Project

CLI tool that renames TV episode files using TMDB metadata and moves them under a sorted `MOVED` tree. Config lives in `config.json` (see `config-example.json`).

## Layout

| Module | Role |
| --- | --- |
| `run.py` | CLI entrypoint, config load, main rename/undo/history flow |
| `file_io.py` | Config validation, filename parsing, rename/move, recursive scan |
| `moviedb.py` | TMDB API client, series search (paginated, capped), error sanitization |
| `series_cache.py` | Persistent TMDB series choices (`series_cache.json`) |
| `history.py` | Rename batches for undo (`rename_history.json`) |
| `log.py` | Logging, `--quiet`, run summary |
| `tests/` | pytest; mirror module names (`test_*.py`) |

No package subfolder: modules sit at the repo root beside `run.py`.

## Setup and verification

```bash
python3 -m venv .venv && source .venv/bin/activate
make install.dev
make ci
```

If `make` fails because `python` is missing, use `python3` and invoke tools via `python3 -m` (e.g. `python3 -m pytest`, `python3 -m ruff check .`).

**Before finishing a change:** run the full CI recipe (`make ci` or equivalent). CI uses Python **3.12** and **3.14**; local **3.12+** is enough for development.

## Change checklist

1. **Scope** — Smallest correct diff; match existing style (tabs, single quotes, 100-char lines).
2. **Tests** — Behavior changes need tests in `tests/`. Keep **total coverage ≥ 95%** (see `.coveragerc`).
3. **Types** — basedpyright must pass (`make typecheck`).
4. **Towncrier** — Add `changes/<issue>.<type>.md` for user-facing or release-noted work (`feature`, `bugfix`, `doc`, `misc`). PRs run `towncrier check`.
5. **Docs** — Update `README.md` when CLI flags, config keys, or user-visible behavior change.
6. **PR body** — One `Fixes #N` line per closed issue (not combined on one line).

## Conventions

- **Indentation:** tabs (Ruff `indent-style = "tab"`). Do not convert the repo to spaces.
- **Imports:** Ruff isort rules apply; keep module-level imports consistent with neighboring files.
- **Secrets:** Never commit real TMDB keys; tests should mock HTTP/TMDB.
- **Safety:** Do not overwrite or delete user media on ambiguous paths; prefer skip/log over destructive defaults (see existing `rename_and_move` behavior).

## Releases

Do not bump `pyproject.toml` version or run `make release` unless the task explicitly asks for a release. Maintainers use [RELEASE.md](RELEASE.md).

## Further reading

- [CONTRIBUTING.md](CONTRIBUTING.md) — commands, coverage, Towncrier, style
- [README.md](README.md) — usage and configuration
- [RELEASE.md](RELEASE.md) — changelog and tagging
