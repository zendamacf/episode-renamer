# Release

Episode Renamer uses [Towncrier](https://towncrier.readthedocs.io/) for changelog management and a tag-based GitHub Actions workflow for publishing releases.

**Current version:** 0.1.0

## How releases work

### During development

Add a news fragment to `changes/` in each pull request that includes a user-facing change:

```bash
pip install towncrier
towncrier create 42.feature.md --content "Added dry-run mode"
```

| Type | Use for |
| --- | --- |
| `feature` | New functionality |
| `bugfix` | Bug fixes |
| `doc` | Documentation changes |
| `misc` | Internal changes (listed without detail) |

The issue number can be a GitHub issue or PR number. CI runs `towncrier check` to validate fragments.

Dependabot pull requests get a `misc` fragment committed automatically by CI before the check runs.

### Cutting a release

1. Bump `version` in `pyproject.toml`.
2. Build the changelog (removes consumed fragments and updates `CHANGELOG.md`):

   ```bash
   towncrier build --version 0.1.1
   ```

3. Commit the version bump and changelog update.
4. Tag and push:

   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

The [release workflow](.github/workflows/release.yml) verifies the tag matches `pyproject.toml`, ensures no fragments remain in `changes/`, runs tests, and publishes a GitHub release using the matching `CHANGELOG.md` section.

Install towncrier with `pip install towncrier`.

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
