# Episode Renamer

[![Tests](https://github.com/zendamacf/episode-renamer/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/zendamacf/episode-renamer/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/zendamacf/episode-renamer/branch/main/graph/badge.svg)](https://codecov.io/gh/zendamacf/episode-renamer)

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Common tasks are run via the [Makefile](Makefile):

| Command | What it runs |
| --- | --- |
| `make lint` | Format check and Ruff lint |
| `make format` | Apply Ruff formatting, then lint |
| `make typecheck` | basedpyright |
| `make test` | pytest |
| `make check` | `lint` + `typecheck` |
| `make release VERSION=0.2.1` | Prep release (bump version + changelog) |

CI runs `make check` and `make test`. See [RELEASE.md](RELEASE.md) for changelog and release steps.

