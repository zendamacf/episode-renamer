# Release

Episode Renamer uses [Towncrier](https://towncrier.readthedocs.io/) for changelog management and a tag-based GitHub Actions workflow for publishing releases.

## How releases work

### During development

Add a news fragment to `changes/` in each pull request that includes a user-facing change:

```bash
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

1. Prep the release (bumps `version` in `pyproject.toml` and builds the changelog):

   ```bash
   make release VERSION=0.2.1
   ```

2. Commit the version bump and changelog update.
3. Tag and push:

   ```bash
   git tag v0.2.1
   git push origin v0.2.1
   ```

The [release workflow](.github/workflows/release.yml) verifies the tag matches `pyproject.toml`, ensures no fragments remain in `changes/`, runs checks, tests, and publishes a GitHub release using the matching `CHANGELOG.md` section.
