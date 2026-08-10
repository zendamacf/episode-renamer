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

## Usage

```bash
python run.py           # rename and move files
python run.py --dryrun  # preview changes without modifying files
python run.py --undo    # undo the last rename batch
python run.py --undo 2  # undo the last two rename batches
python run.py --undo --dryrun  # preview what undo would restore
```

`--dryrun` does not move files, but it still calls TMDB and uses API quota.

Successful renames are recorded in `rename_history.json` (next to `config.json`). Undo moves files back to `HOME` and removes empty show/season folders.

### Supported input filenames

The tool parses series name, season, and episode from filenames matching common TV naming patterns:

- `The Office S01E01.mp4`
- `The Office 1x01.mkv`
- `The Office 102.avi` (compact `S01E02` style)
- `The Office 2005 S02E03.m4v`

Supported video extensions: `mp4`, `mkv`, `avi`, `flv`, `m4v`.

Dots in series names are treated as spaces (e.g. `The.Office.S01E01.mp4` → "The Office").

### Output structure

Files are renamed to `S01E01 - Episode Title.ext` and moved under:

```
MOVED/
  Show Name (2005)/
    Season 1/
      S01E01 - Pilot.mp4
```

When multiple TMDB series match a filename, the tool prompts for the correct one. Series choices are cached for the duration of a run. Enter `i` to skip a file.

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
