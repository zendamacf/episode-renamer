#!/usr/bin/env python3

import argparse

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


def main(dryrun: bool) -> None:
	"""
	Main function
	"""
	log.info('Running renamer...')
	if dryrun:
		log.warn('[DRY-RUN] No files will be moved')

	config = io.read_config('config.json')

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
			if f['name'] in matches:
				# Have previously used this series, so use it again
				chosen = matches[f['name']]
				log.info(
					f"Using previous match {_series_label(chosen)} for {f['name']}"
				)
			else:
				# New series, so look it up
				series_list = moviedb.get_series(
					f['name'], config['MOVIEDB_KEY']
				)
				if not series_list:
					log.warn('No series matches for {}'.format(f['name']))
					skipped += 1
					continue

				if len(series_list) == 1:
					chosen = series_list[0]
					log.info(
						f"Matched {_series_label(chosen)} for {f['name']}"
					)
				else:
					chosen = io.prompt_user(f['name'], series_list)
					if chosen is None:
						log.warn('Ignoring {}'.format(f['name']))
						skipped += 1
						continue
					log.info(
						f"Selected {_series_label(chosen)} for {f['name']}"
					)

				# Save for future lookups
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
				skipped += 1
				continue

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
				skipped += 1
			else:
				io.rename_and_move(
					config['HOME'],
					f['filename'],
					config['MOVED'],
					new_filename,
					chosen['name'],
					chosen['year'],
					f['season']
				)
				moved += 1
		except io.FileIOException as e:
			log.error(f"Failed processing {f['filename']}: {e}")
			failed += 1

	summary = f'Done: {moved} moved, {skipped} skipped, {failed} failed'
	if failed:
		log.warn(summary)
	else:
		log.info(summary)


if __name__ == '__main__':
	args = parser.parse_args()
	main(args.dryrun)
