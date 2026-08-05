#!/usr/bin/env python3
"""
Bump the project version and build the towncrier changelog.

Usage:
	./scripts/prep_release.py 0.2.1
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / 'pyproject.toml'

VERSION_LINE = re.compile(r'^version = "([^"]+)"', re.MULTILINE)
SEMVER = re.compile(r'^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$')


def read_version(text: str) -> str:
	match = VERSION_LINE.search(text)
	if not match:
		raise SystemExit(f'Could not find version in {PYPROJECT}')
	return match.group(1)


def bump_pyproject(version: str) -> str:
	text = PYPROJECT.read_text()
	old = read_version(text)
	if old == version:
		raise SystemExit(f'pyproject.toml is already at {version}')
	updated, count = VERSION_LINE.subn(f'version = "{version}"', text, count=1)
	if count != 1:
		raise SystemExit(f'Failed to bump version in {PYPROJECT}')
	PYPROJECT.write_text(updated)
	return old


def stage_pyproject() -> None:
	subprocess.run(
		['git', 'add', '--', str(PYPROJECT)],
		cwd=ROOT,
		check=True,
	)


def build_changelog(version: str) -> None:
	subprocess.run(
		['towncrier', 'build', '--version', version, '--yes'],
		cwd=ROOT,
		check=True,
	)


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description='Bump version and build the towncrier changelog.')
	parser.add_argument(
		'version',
		help='New release version (e.g. 0.2.1)',
	)
	args = parser.parse_args(argv)

	if not SEMVER.match(args.version):
		raise SystemExit(
			f'Invalid version {args.version!r}; expected N.N.N (optional aN/bN/rcN suffix)'
		)

	old = bump_pyproject(args.version)
	# Towncrier stages the changelog & removed change fragments, also stage pyproject
	stage_pyproject()
	print(f'Bumped version {old} -> {args.version}')

	try:
		build_changelog(args.version)
	except FileNotFoundError:
		raise SystemExit('towncrier not found; install with: pip install towncrier') from None
	except subprocess.CalledProcessError as exc:
		return exc.returncode

	print(
		'Release prep complete. Next:\n'
		f'	1. Review CHANGELOG.md and pyproject.toml\n'
		f'	2. Commit the release prep changes\n'
		f'	3. git tag v{args.version} && git push origin v{args.version}'
	)
	return 0


if __name__ == '__main__':
	sys.exit(main())
