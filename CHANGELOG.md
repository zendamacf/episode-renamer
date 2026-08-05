# Changelog

All notable changes to this project will be documented in this file.

<!-- towncrier release notes start -->

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
