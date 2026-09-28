# Contributing

Thanks for helping improve Episode Renamer. This guide covers local setup, checks, changelog fragments, and release prep. User-facing usage lives in [README.md](README.md). Coding agents should start with [AGENTS.md](AGENTS.md).

## Python and environment

- **Python 3.12+** is required ([`.python-version`](./.python-version)).
- Use a virtual environment:

  ```bash
  python -m venv .venv
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  make install.dev
  ```

`make install.dev` installs runtime and dev dependencies from `requirements-dev.txt` (Ruff, basedpyright, pytest, Towncrier, and related tools).

## Commands

Most workflows go through the [Makefile](Makefile):

| Command | Purpose |
| --- | --- |
| `make install` | Runtime dependencies only |
| `make install.dev` | Runtime + dev dependencies |
| `make lint` | Ruff format check and lint |
| `make format` | Apply Ruff formatting, then lint |
| `make typecheck` | basedpyright |
| `make test` | pytest with coverage |
| `make check` | `lint` + `typecheck` |
| `make ci` | `check` + `test` (same as CI) |

Run **`make ci`** before opening a pull request when you can; GitHub Actions runs the same steps on supported Python versions.

## Test coverage

Coverage is configured in [`.coveragerc`](.coveragerc). **Total coverage must stay at or above 95%.** pytest enforces this via the dev dependencies; CI reports to Codecov. Add or extend tests when you change behavior that is not already covered.

## Changelog (Towncrier)

User-facing or notable changes need a news fragment under [`changes/`](changes/):

```bash
towncrier create 42.feature.md --content "Added dry-run mode"
```

| Fragment type | Use for |
| --- | --- |
| `feature` | New functionality |
| `bugfix` | Bug fixes |
| `doc` | Documentation |
| `misc` | Internal or non-user-facing changes (listed without detail) |

Use the GitHub issue or PR number in the filename (e.g. `61.doc.md`). Pull requests run **`towncrier check`** to ensure fragments are valid. Dependabot PRs get a `misc` fragment added automatically in CI.

Full release and changelog workflow: [RELEASE.md](RELEASE.md).

## Releases

Maintainers cut releases with:

```bash
make release VERSION=x.y.z
```

That bumps `version` in `pyproject.toml` and updates `CHANGELOG.md`. See [RELEASE.md](RELEASE.md) for tagging and the GitHub release workflow.

## Code style

- **Indentation:** tabs (not spaces). Ruff is configured with `indent-style = "tab"`; tab-related flake8 rules are intentionally ignored in [`pyproject.toml`](pyproject.toml).
- **Line length:** 100 characters.
- **Quotes:** single quotes (Ruff format).
- **Lint:** Ruff (`E`, `F`, `W`, `I`, `UP`, `B`, `SIM`).
- **Types:** basedpyright in `standard` mode for Python 3.12.

Use `make format` to apply formatting; use `make lint` to verify without writing files.

## Pull requests

1. Branch from `main`.
2. Add a Towncrier fragment when appropriate.
3. Run `make ci` locally.
4. Describe what changed and link related issues.

Questions or ideas are welcome in [GitHub issues](https://github.com/zendamacf/episode-renamer/issues).
