#!/usr/bin/env python3

import file_io as io
import tvdb


def main():
	"""
	Main function
	"""
	print('Running renamer...')
	config = io.read_config('config.json')

	found = io.find_files(config['HOME'])
	if len(found) == 0:
		print('No files found')
		return

	tvdb_token = tvdb.login(config['TVDB_KEY'], config['TVDB_USER'], config['TVDB_NAME'])

	for f in found:
		series_list = tvdb.get_series(f['name'], tvdb_token)
		if not series_list:
			print('No series matches for {}'.format(f['name']))
			continue

		if len(series_list) == 1:
			chosen = series_list[0]
		else:
			chosen = io.prompt_user(f['name'], series_list)
			if chosen is None:
				print('Ignoring {}'.format(f['name']))
				continue

		episodename = tvdb.get_episode(chosen['id'], f['season'], f['episode'], tvdb_token)
		if episodename is None:
			print('No episode found for {} S{}E{}'.format(f['name'], f['season'], f['episode']))
			continue

		new_filename = io.get_filename(
			f['filename'],
			f['season'],
			f['episode'],
			episodename,
			f['extension']
		)
		io.rename_and_move(
			config['HOME'],
			f['filename'],
			config['MOVED'],
			new_filename,
			chosen['name'],
			chosen['year'],
			f['season']
		)


main()
