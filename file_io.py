"""
Searches for tv show episode files, and renames & sorts, them
using information from thetvdb
"""

import json
import os
import re
import shutil


class FileIOException(Exception):
	pass


def read_config(filename: str) -> dict:
	"""
	Reads a JSON config file into a dict
	"""
	with open(filename) as file:
		config = json.load(file)

	return config


def find_files(directory) -> list:
	"""
	Gets a list of video files in a given directory
	"""
	print('Checking for files in {}'.format(directory))
	found = []
	for filename in sorted(os.listdir(directory), key=str.lower):
		if os.path.isfile(os.path.join(directory, filename)):
			if is_video_file(filename):
				try:
					found.append(parse_filename(filename))
				except FileIOException as e:
					print(f'Error parsing {filename}: {repr(e)}')
	return found


def is_video_file(filename: str) -> bool:
	"""
	Returns True if the file has an extension indicating it's a video file
	"""
	return filename.rsplit('.', 1)[1] in ['mp4', 'flv', 'avi', 'mkv', 'm4v']


def parse_filename(filename: str) -> dict:
	"""
	Uses regex to pull series name, season and episode numbers
	"""
	regex_parsers = [
		r"^(?P<name>.*?)\.*?(\d{4})?\.*?s *(?P<s>\d+) *e *(?P<e>\d+).*\.(?P<ext>.*?)$",
		r"^(?P<name>.*?)(?P<s>\d+)x(?P<e>\d+).*\.(?P<ext>.*?)$",
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
			print('({}) {} ({})'.format(count + 1, value['name'], value['year']))
		else:
			print('({}) {}'.format(count + 1, value['name']))
	choice = input(f'Select correct series for {orig_name} ("i" to ignore): ')
	if choice == '':
		chosen = series_list[0]
	elif choice == 'i':
		return None
	elif int(choice) < 1 or int(choice) > len(series_list):
		raise FileIOException('Invalid input.')
	else:
		chosen = series_list[int(choice) - 1]

	return chosen


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
	print('Current: {}'.format(filename))
	print('New: {}'.format(new_filename))
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
	if year is not None:
		show_folder = os.path.join(new_directory, '{} ({})'.format(show, year))
	else:
		show_folder = os.path.join(new_directory, '{}'.format(show))
	if not os.path.exists(show_folder):
		os.makedirs(show_folder)
	season_folder = os.path.join(show_folder, 'Season {}'.format(season,))
	if not os.path.exists(season_folder):
		os.makedirs(season_folder)
	curr_file = os.path.join(orig_directory, orig_filename)
	new_file = os.path.join(season_folder, new_filename)
	if os.path.exists(new_file):
		raise FileIOException('{} already Exists.'.format(new_file,))
	shutil.move(curr_file, new_file)
	print('Successfully moved.')
