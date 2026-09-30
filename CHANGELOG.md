# Changelog

All notable changes to this project will be documented in this file.

<!-- towncrier release notes start -->

## [1.0.0](https://github.com/zendamacf/episode-renamer/releases/tag/v1.0.0) (2026-09-30)

### Features

- Configurable default subtitle language and preservation of language tags from source filenames. ([#53](https://github.com/zendamacf/episode-renamer/issues/53))
- Persist TMDB series selections in ``series_cache.json`` between runs. ([#54](https://github.com/zendamacf/episode-renamer/issues/54))
- Interactive TMDB search pagination: load one page at a time with ``n`` for more (capped at 3 pages). ([#55](https://github.com/zendamacf/episode-renamer/issues/55))
- Optional recursive scan of ``HOME`` via ``--recursive`` or ``RECURSIVE_SCAN`` in config. ([#56](https://github.com/zendamacf/episode-renamer/issues/56))
- ``--quiet`` mode for scripting: errors and final batch summary only. ([#57](https://github.com/zendamacf/episode-renamer/issues/57))
- Add `--history` to list recorded rename batches before undoing.
- Include origin country in the interactive prompt when multiple TMDB series match.
- Move matching subtitle companions with episodes, renaming them to `SxxExx - Title.en.<ext>`.
- Use a year from the filename to auto-select the matching TMDB series when unique.

### Bug Fixes

- Skip moves when the destination filename already exists (no overwrite or source deletion). ([#58](https://github.com/zendamacf/episode-renamer/issues/58))
- Reject ``config.json`` when ``HOME`` and ``MOVED`` are the same path or nest inside each other. ([#60](https://github.com/zendamacf/episode-renamer/issues/60))
- Sanitize TMDB client error messages so API keys and raw response bodies are not shown. ([#62](https://github.com/zendamacf/episode-renamer/issues/62))
- Clear, actionable CLI message when ``config.json`` is missing instead of an unhandled traceback. ([#63](https://github.com/zendamacf/episode-renamer/issues/63))

### Documentation

- Add CONTRIBUTING.md and AGENTS.md with setup, checks, Towncrier, and style notes. ([#61](https://github.com/zendamacf/episode-renamer/issues/61))

### Misc

- [#42](https://github.com/zendamacf/episode-renamer/issues/42), [#43](https://github.com/zendamacf/episode-renamer/issues/43), [#44](https://github.com/zendamacf/episode-renamer/issues/44), [#45](https://github.com/zendamacf/episode-renamer/issues/45), [#46](https://github.com/zendamacf/episode-renamer/issues/46), [#47](https://github.com/zendamacf/episode-renamer/issues/47), [#48](https://github.com/zendamacf/episode-renamer/issues/48), [#49](https://github.com/zendamacf/episode-renamer/issues/49), [#50](https://github.com/zendamacf/episode-renamer/issues/50), [#51](https://github.com/zendamacf/episode-renamer/issues/51), [#52](https://github.com/zendamacf/episode-renamer/issues/52), [#59](https://github.com/zendamacf/episode-renamer/issues/59)


## [0.2.1](https://github.com/zendamacf/episode-renamer/releases/tag/v0.2.1) (2026-08-10)

### Features

- Improve CLI log readability with bold, fixed-width colored prefixes and uncolored message bodies.

### Documentation

- Move product install and usage docs into the README and link the required Python version to .python-version.

### Misc

- [#30](https://github.com/zendamacf/episode-renamer/issues/30), [#31](https://github.com/zendamacf/episode-renamer/issues/31), [#32](https://github.com/zendamacf/episode-renamer/issues/32), [#33](https://github.com/zendamacf/episode-renamer/issues/33), [#34](https://github.com/zendamacf/episode-renamer/issues/34), [#35](https://github.com/zendamacf/episode-renamer/issues/35)
- Add a Makefile for running common scripts e.g. Ruff lint/format checks, basedpyright type checking, pytest testing, etc.
- Add a prep_release script that bumps the project version and builds the towncrier changelog.
- Add file match pattern for anime encoder prefixes e.g. `[Judas]`.
- Add make install and make ci for local bootstrap and CI parity.
- Drop show/season folder creation log lines from rename output.
- Enable pip caching in CI and Dependabot updates for GitHub Actions.
- Split lint/typecheck into its own workflow and Dependabot changelog into a separate job.
- Widen Ruff lint selects beyond flake8-parity E/F/W rules.


## [0.2.0](https://github.com/zendamacf/episode-renamer/releases/tag/v0.2.0) (2026-08-05)

### Features

- Add `--undo` / `--undo N` to reverse the last rename batch(es), with dry-run preview and a persistent rename journal.
- Add colored CLI output for status, success, warning, and error messages.
- Improve CLI status messages with file counts, match confirmations, destinations, and a run summary.

### Misc

- [#12](https://github.com/zendamacf/episode-renamer/issues/12)
- Add TMDB request timeouts, bounded retries for transient failures, and safer response parsing.
- Align release CI to Python 3.14, allow MOVIEDB_KEY from the environment, and warn that dry-run still uses TMDB quota.
- Isolate per-file MovieDB and filesystem errors so one failure does not abort the batch.
- Sanitise show folder names and harden destination moves against races and cross-device copies.
- Validate required config keys and accept case-insensitive video extensions.


## [0.1.0](https://github.com/zendamacf/episode-renamer/releases/tag/v0.1.0) (2025-06-20)

Initial release.
