#!/usr/bin/env python3

import argparse
import os
from typing import Literal

import file_io as io
import log
import moviedb

parser = argparse.ArgumentParser(prog='Episode Renamer')
parser.add_argument(
	'--dryrun',
	action='store_true',
	help='Instead of renaming the files, just display what changes would be made.'
)


def _series_label(series: dict) -> str:
	if series.get('year') is not None:
		return f"{series['name']} ({series['year']})"
	return series['name']


def _process_file(
	f: dict,
	config: dict,
	matches: dict,
	dryrun: bool,
) -> Literal['moved', 'skipped']:
	"""
	Resolve metadata and optionally rename one file.

	Returns 'moved' or 'skipped'. Raises on hard failures so the caller can
	isolate the error and continue the batch.
	"""
	if f['name'] in matches:
		chosen = matches[f['name']]
		log.info(
			f"Using previous match {_series_label(chosen)} for {f['name']}"
		)
	else:
		series_list = moviedb.get_series(f['name'], config['MOVIEDB_KEY'])
		if not series_list:
			log.warn('No series matches for {}'.format(f['name']))
			return 'skipped'

		if len(series_list) == 1:
			chosen = series_list[0]
			log.info(f"Matched {_series_label(chosen)} for {f['name']}")
		else:
			chosen = io.prompt_user(f['name'], series_list)
			if chosen is None:
				log.warn('Ignoring {}'.format(f['name']))
				return 'skipped'
			log.info(f"Selected {_series_label(chosen)} for {f['name']}")

		matches[f['name']] = chosen

	episodename = moviedb.get_episode(
		chosen['id'],
		f['season'],
		f['episode'],
		config['MOVIEDB_KEY']
	)
	if episodename is None:
		log.warn(
			f"No episode found for {f['name']} "
			f"S{f['season']}E{f['episode']}"
		)
		return 'skipped'

	new_filename = io.get_filename(
		f['filename'],
		f['season'],
		f['episode'],
		episodename,
		f['extension']
	)
	if dryrun:
		log.warn(
			f"[DRY-RUN] Skipping rename from {f['filename']} "
			f"to {new_filename}"
		)
		return 'skipped'

	io.rename_and_move(
		config['HOME'],
		f['filename'],
		config['MOVED'],
		new_filename,
		chosen['name'],
		chosen['year'],
		f['season']
	)
	return 'moved'


def main(dryrun: bool) -> None:
	"""
	Main function
	"""
	log.info('Running renamer...')
	if dryrun:
		log.warn('[DRY-RUN] No files will be moved')

	config = io.read_config('config.json')
	env_key = os.environ.get('MOVIEDB_KEY')
	if env_key:
		config['MOVIEDB_KEY'] = env_key
		log.info('Using MOVIEDB_KEY from environment')

	found = io.find_files(config['HOME'])
	if len(found) == 0:
		log.warn('No files found')
		return

	log.info(f'Found {len(found)} file(s)')

	matches = {}
	moved = 0
	skipped = 0
	failed = 0

	for f in found:
		try:
			result = _process_file(f, config, matches, dryrun)
		except (moviedb.MovieDBException, io.FileIOException, OSError) as e:
			log.error(f"Failed processing {f['filename']}: {e}")
			failed += 1
			continue

		if result == 'moved':
			moved += 1
		else:
			skipped += 1

	summary = f'Done: {moved} moved, {skipped} skipped, {failed} failed'
	if failed:
		log.warn(summary)
	else:
		log.info(summary)


if __name__ == '__main__':
	args = parser.parse_args()
	main(args.dryrun)
