# Release

Episode Renamer uses [release-please](https://github.com/googleapis/release-please) to automate versioning, changelog updates, and GitHub releases.

**Current version:** 0.1.0

## How releases work

1. Merge changes to `main` using [Conventional Commits](https://www.conventionalcommits.org/).
2. Release-please opens a release PR that bumps the version, updates `CHANGELOG.md`, and syncs version files.
3. Merge the release PR → a GitHub release and tag (e.g. `v0.1.1`) are created automatically.

No manual tagging is required.

### Commit message format

| Prefix | Effect (while &lt; 1.0.0) | Example |
| --- | --- | --- |
| `feat:` | Patch bump | `feat: cache series lookups across files` |
| `fix:` | Patch bump | `fix: skip files with unparseable names` |
| `feat!:` or `BREAKING CHANGE:` | Minor bump | `feat!: require Python 3.12` |

Other prefixes (`chore:`, `docs:`, `test:`, etc.) do not trigger a release on their own.

### Files managed by release-please

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Package version |
| `.release-please-manifest.json` | Last released version |
| `CHANGELOG.md` | Version history |

Configuration lives in `release-please-config.json`. The workflow is defined in `.github/workflows/release-please.yml`.

### Before merging a release PR

The test workflow (`.github/workflows/test.yml`) runs on every pull request, including release PRs. Ensure CI is green before merging.

If release-please cannot open PRs, check that GitHub Actions is allowed to create and approve pull requests in the repository (or organization) settings.

---

## v0.1.0

Rename TV episode video files using metadata from [The Movie Database (TMDB)](https://www.themoviedb.org/) and organize them into a sorted folder structure.

### Requirements

- Python 3.12+
- A TMDB API key ([create one here](https://www.themoviedb.org/settings/api))
- Network access to `api.themoviedb.org`

### Installation

```bash
git clone https://github.com/zendamacf/episode-renamer.git
cd episode-renamer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config-example.json config.json
```

Edit `config.json` with your TMDB API key and directory paths.

### Configuration

| Key | Description |
| --- | --- |
| `MOVIEDB_KEY` | TMDB API key |
| `HOME` | Directory containing unsorted episode files |
| `MOVED` | Destination root for renamed and sorted files |

### Usage

```bash
python run.py           # rename and move files
python run.py --dryrun  # preview changes without modifying files
```

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

### License

MIT — see [LICENSE](LICENSE).
