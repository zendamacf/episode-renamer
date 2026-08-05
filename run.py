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


def main(dryrun: bool) -> None:
	"""
	Main function
	"""
	log.info('Running renamer...')
	config = io.read_config('config.json')

	found = io.find_files(config['HOME'])
	if len(found) == 0:
		log.warn('No files found')
		return

	matches = {}

	for f in found:
		if f['name'] in matches:
			# Have previously used this series, so use it again
			chosen = matches[f['name']]
			log.info(f"Using previous match {chosen['name']} for {f['name']}")
		else:
			# New series, so look it up
			series_list = moviedb.get_series(f['name'], config['MOVIEDB_KEY'])
			if not series_list:
				log.warn('No series matches for {}'.format(f['name']))
				continue

			if len(series_list) == 1:
				chosen = series_list[0]
			else:
				chosen = io.prompt_user(f['name'], series_list)
				if chosen is None:
					log.warn('Ignoring {}'.format(f['name']))
					continue

			# Save for future lookups
			matches[f['name']] = chosen

		episodename = moviedb.get_episode(
			chosen['id'],
			f['season'],
			f['episode'],
			config['MOVIEDB_KEY']
		)
		if episodename is None:
			log.warn(f"No episode found for {f['name']} S{f['season']}E{f['episode']}")
			continue

		new_filename = io.get_filename(
			f['filename'],
			f['season'],
			f['episode'],
			episodename,
			f['extension']
		)
		if dryrun:
			log.warn(f"[DRYRUN] Skipping rename from {f['filename']} to {new_filename}")
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


if __name__ == '__main__':
	args = parser.parse_args()
	main(args.dryrun)
