# Episode Renamer

[![Tests](https://github.com/zendamacf/episode-renamer/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/zendamacf/episode-renamer/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/zendamacf/episode-renamer/branch/main/graph/badge.svg)](https://codecov.io/gh/zendamacf/episode-renamer)

Rename TV episode video files using metadata from [The Movie Database (TMDB)](https://www.themoviedb.org/) and organize them into a sorted folder structure.

## Requirements

- Python ([version set here](./.python-version))
- A TMDB API key ([create one here](https://www.themoviedb.org/settings/api))
- Network access to `api.themoviedb.org`

## Installation

```bash
git clone https://github.com/zendamacf/episode-renamer.git
cd episode-renamer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config-example.json config.json
```

Edit `config.json` with your TMDB API key and directory paths.

## Configuration

| Key | Description |
| --- | --- |
| `MOVIEDB_KEY` | TMDB API key (can also be set via the `MOVIEDB_KEY` environment variable, which overrides the config file) |
| `HOME` | Directory containing unsorted episode files |
| `MOVED` | Destination root for renamed and sorted files |
| `SUBTITLE_LANG` | Optional. Default language tag for renamed subtitles when the source file has no tag (default: `en`). Overridden by the `SUBTITLE_LANG` environment variable. |
| `RECURSIVE_SCAN` | Optional. When `true`, scan nested folders under `HOME` for videos (default: `false`). |

## Usage

```bash
python run.py           # rename and move files
python run.py --dryrun  # preview changes without modifying files
python run.py --quiet   # errors and final summary only (for cron/scripts)
python run.py --recursive  # scan nested folders under HOME (overrides RECURSIVE_SCAN)
python run.py --history # list recorded rename batches
python run.py --undo    # undo the last rename batch
python run.py --undo 2  # undo the last two rename batches
python run.py --undo --dryrun  # preview what undo would restore
python run.py --undo --quiet   # undo with minimal output
```

With `--quiet`, a successful rename run prints only the final `Done:` summary (plus any `Error:` lines). Example for a wrapper script:

```bash
python run.py --quiet || exit 1
```

`--dryrun` does not move files, but it still calls TMDB and uses API quota.

Successful renames are recorded in `rename_history.json` (next to `config.json`). `--history` lists each batch with its id, file count, undo index (`undo 1` is the newest batch), and src → dest paths. Undo moves files back to `HOME` and removes empty show/season folders.

TMDB series choices (from prompts or automatic single matches) are saved in `series_cache.json` beside `config.json`. Keys are the parsed show name and optional filename year; values store the TMDB id, name, year, and country. Later runs reuse the cache after verifying the id still appears in TMDB search results. Delete `series_cache.json` to clear cached selections and be prompted again.

### Supported input filenames

The tool parses series name, season, and episode from filenames matching common TV naming patterns:

- `The Office S01E01.mp4`
- `The Office 1x01.mkv`
- `The Office 102.avi` (compact `S01E02` style)
- `The Office 2005 S02E03.m4v`
- `The.Office.(2005).S01E01.mkv`

When a year appears between the show name and season/episode marker, it is used to prefer the matching TMDB series and skip the interactive prompt when only one result matches that year. If multiple TMDB results share the same year, the tool still prompts.

Supported video extensions: `mp4`, `mkv`, `avi`, `flv`, `m4v`.

Matching subtitle companions next to a video (same basename, optionally with a language tag) are moved with it:

- `The Office S01E01.srt` → `S01E01 - Pilot.en.srt` (uses `SUBTITLE_LANG` when no tag is present)
- `The Office S01E01.fr.srt` → `S01E01 - Pilot.fr.srt` (preserves the source language tag)
- `The Office S01E01.en.srt` → `S01E01 - Pilot.en.srt`

Supported subtitle extensions: `srt`, `ass`, `ssa`, `vtt`, `sub`. Renamed subtitles use `.<lang>.<ext>` where `lang` comes from the source filename when present, otherwise from `SUBTITLE_LANG` (default `en`).

Dots in series names are treated as spaces (e.g. `The.Office.S01E01.mp4` → "The Office").

### Output structure

Files are renamed to `S01E01 - Episode Title.ext` (subtitles: `S01E01 - Episode Title.en.ext`) and moved under:

```
MOVED/
  Show Name (2005)/
    Season 1/
      S01E01 - Pilot.mp4
      S01E01 - Pilot.en.srt
```

When multiple TMDB series match a filename, the tool loads the first TMDB search page and prompts for the correct one. Enter `n` at the prompt to load the next page (up to 3 pages per search, to limit API usage). Enter `i` to skip a file. Series choices are saved in `series_cache.json` for later runs.

If the target filename already exists under `MOVED`, the renamer **skips** the move (nothing is overwritten or deleted; any copy still in `HOME` is left in place). Skipped moves are not added to `rename_history.json`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
make install.dev
```

Common tasks are run via the [Makefile](Makefile):

| Command | What it runs |
| --- | --- |
| `make install` | Install runtime dependencies |
| `make install.dev` | Install runtime + dev dependencies |
| `make lint` | Format check and Ruff lint |
| `make format` | Apply Ruff formatting, then lint |
| `make typecheck` | basedpyright |
| `make test` | pytest |
| `make check` | `lint` + `typecheck` |
| `make ci` | `check` + `test` (what CI runs) |
| `make release VERSION=0.2.2` | Prep release (bump version + changelog) |

See [RELEASE.md](RELEASE.md) for changelog and release steps.

## Deployment

```bash
python -m venv .venv
source .venv/bin/activate
make install
```
## License

MIT — see [LICENSE](LICENSE).
