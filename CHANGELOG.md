# Changelog

All notable changes to this project will be documented in this file.

<!-- towncrier release notes start -->

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
