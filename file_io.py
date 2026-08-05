"""
Searches for tv show episode files, and renames & sorts, them
using information from TMDB
"""

import json
import os
import re
import shutil

import log


class FileIOException(Exception):
	pass


REQUIRED_CONFIG_KEYS = ('MOVIEDB_KEY', 'HOME', 'MOVED')


def read_config(filename: str) -> dict:
	"""
	Reads a JSON config file into a dict
	"""
	with open(filename) as file:
		config = json.load(file)

	missing = [k for k in REQUIRED_CONFIG_KEYS if not config.get(k)]
	if missing:
		raise FileIOException(
			'Missing or empty config keys: {}'.format(', '.join(missing))
		)
	return config


def find_files(directory) -> list:
	"""
	Gets a list of video files in a given directory
	"""
	log.info('Checking for files in {}'.format(directory))
	found = []
	for filename in sorted(os.listdir(directory), key=str.lower):
		if os.path.isfile(os.path.join(directory, filename)):
			if is_video_file(filename):
				try:
					found.append(parse_filename(filename))
				except FileIOException as e:
					log.error(f'Error parsing {filename}: {repr(e)}')
	return found


def is_video_file(filename: str) -> bool:
	"""
	Returns True if the file has an extension indicating it's a video file
	"""
	parts = filename.rsplit('.', 1)
	if len(parts) == 1:
		return False
	return parts[1].lower() in {'mp4', 'flv', 'avi', 'mkv', 'm4v'}


def parse_filename(filename: str) -> dict:
	"""
	Uses regex to pull series name, season and episode numbers
	"""
	regex_parsers = [
		# S##E## style, optional year: "Show.S01E01.mkv", "Show 2020 S01E01.mp4"
		r"^(?P<name>.*?)\.*?(\d{4})?\.*?s *(?P<s>\d+) *e *(?P<e>\d+).*\.(?P<ext>.*?)$",
		# Season x episode: "Show 1x01.mkv", "Show.12x05.avi"
		r"^(?P<name>.*?)(?P<s>\d+)x(?P<e>\d+).*\.(?P<ext>.*?)$",
		# Packed season+episode digits: "Show 101.mp4" → S1E01, "Show.1205.mkv" → S12E05
		r"^(?P<name>(?:.*?\D|))(?P<s>\d{1,2})(?P<e>\d{2})(?:\D.*|)\.(?P<ext>.*?)$",
	]
	for parser in regex_parsers:
		matches = re.compile(parser, re.IGNORECASE).search(filename)
		try:
			match_dict = matches.groupdict()
			break
		except AttributeError:
			continue
	else:
		raise FileIOException('Filename not matched.')

	return {
		'name': match_dict['name'].replace('.', ' ').strip(),
		'season': int(match_dict['s']),
		'episode': int(match_dict['e']),
		'filename': filename,
		'extension': match_dict['ext']
	}


def prompt_user(orig_name: str, series_list: list) -> dict:
	"""
	Prompt user to select which show this episode is from
	"""
	for count, value in enumerate(series_list):
		if value['year'] is not None:
			log.plain('({}) {} ({})'.format(count + 1, value['name'], value['year']))
		else:
			log.plain('({}) {}'.format(count + 1, value['name']))
	choice = input(log.prompt(
		f'Select correct series for {orig_name} ("i" to ignore): '
	))
	if choice == '':
		return series_list[0]
	if choice == 'i':
		return None
	try:
		selection = int(choice)
	except ValueError:
		raise FileIOException('Invalid input.')
	if selection < 1 or selection > len(series_list):
		raise FileIOException('Invalid input.')
	return series_list[selection - 1]


def winsafe_filename(filename: str) -> str:
	"""
	Make a windows-safe filename
	"""
	return re.sub(r'[\\/:"*?<>|]+', "", filename)


def get_filename(
	filename: str,
	season: int,
	episode: int,
	episodename: str,
	extension: str
) -> str:
	"""
	Returns the new filename to use.
	"""
	if int(season) < 10:
		season = '0{}'.format(season)
	if int(episode) < 10:
		episode = '0{}'.format(episode)
	new_filename = f'S{season}E{episode} - {episodename}.{extension}'
	log.info('Current: {}'.format(filename))
	log.info('New: {}'.format(new_filename))
	return winsafe_filename(new_filename)


def rename_and_move(
	orig_directory: str,
	orig_filename: str,
	new_directory: str,
	new_filename: str,
	show: str,
	year: str,
	season: int
):
	"""
	Rename and sort the file into folders
	"""
	safe_show = winsafe_filename(str(show))
	if not safe_show:
		raise FileIOException('Show name is empty after sanitization.')
	folder_name = (
		'{} ({})'.format(safe_show, year) if year is not None else safe_show
	)
	show_folder = os.path.join(new_directory, folder_name)
	season_folder = os.path.join(show_folder, 'Season {}'.format(season))

	created_show = not os.path.exists(show_folder)
	created_season = not os.path.exists(season_folder)
	os.makedirs(season_folder, exist_ok=True)
	if created_show:
		log.info(f'Created show folder: {show_folder}')
	if created_season:
		log.info(f'Created season folder: {season_folder}')

	curr_file = os.path.join(orig_directory, orig_filename)
	new_file = os.path.join(season_folder, new_filename)
	try:
		fd = os.open(new_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
		os.close(fd)
	except FileExistsError:
		raise FileIOException('{} already Exists.'.format(new_file))

	try:
		os.replace(curr_file, new_file)
	except OSError:
		# Cross-device: replace reserved dest with content, then remove source.
		try:
			shutil.copy2(curr_file, new_file)
			os.unlink(curr_file)
		except OSError as exc:
			try:
				os.unlink(new_file)
			except OSError:
				pass
			raise FileIOException(
				'Failed to move {} -> {}: {}'.format(curr_file, new_file, exc)
			) from exc

	log.success(f'Successfully moved to {new_file}')
