# Contributing

Thanks for helping improve Episode Renamer. User-facing usage is in [README.md](README.md). Coding agents should start with [AGENTS.md](AGENTS.md).

## Python and environment

- **Python 3.12+** ([`.python-version`](./.python-version)).
- Virtualenv and dev dependencies:

  ```bash
  python -m venv .venv
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  make install.dev
  ```

`make install.dev` installs from `requirements-dev.txt` (Ruff, basedpyright, pytest, Towncrier, etc.).

## Commands

Workflows use the [Makefile](Makefile):

| Command | Purpose |
| --- | --- |
| `make install` | Runtime dependencies only |
| `make install.dev` | Runtime + dev dependencies |
| `make lint` | Ruff format check and lint |
| `make format` | Apply Ruff formatting, then lint |
| `make typecheck` | basedpyright |
| `make test` | pytest with coverage |
| `make check` | `lint` + `typecheck` |
| `make ci` | `check` + `test` (what GitHub Actions runs) |

Run **`make ci`** before opening a pull request when you can.

## Test coverage

[`.coveragerc`](.coveragerc) requires **≥ 95%** total coverage. Add or extend tests when you change uncovered behavior.

## Changelog and releases

News fragments and release tagging are documented in [RELEASE.md](RELEASE.md). Pull requests run **`towncrier check`**.

## Code style

Configured in [`pyproject.toml`](pyproject.toml):

- **Indentation:** tabs (not spaces); Ruff `indent-style = "tab"`.
- **Line length:** 100; **quotes:** single.
- **Lint:** Ruff (`E`, `F`, `W`, `I`, `UP`, `B`, `SIM`).
- **Types:** basedpyright, Python 3.12, `standard` mode.

Use `make format` to apply formatting; `make lint` to verify.

## Pull requests

1. Branch from `main`.
2. Add a Towncrier fragment when appropriate ([RELEASE.md](RELEASE.md#during-development)).
3. Run `make ci`.
4. Describe changes and link issues.

Questions welcome in [GitHub issues](https://github.com/zendamacf/episode-renamer/issues).
