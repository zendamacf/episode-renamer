"""
Searches for tv show episode files, and renames & sorts, them
using information from TMDB
"""

import contextlib
import json
import os
import re
import shutil
from typing import Any

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
		raise FileIOException('Missing or empty config keys: {}'.format(', '.join(missing)))
	return config


def find_files(directory) -> list:
	"""
	Gets a list of video files in a given directory
	"""
	log.info(directory, prefix='Checking')
	found = []
	for filename in sorted(os.listdir(directory), key=str.lower):
		if os.path.isfile(os.path.join(directory, filename)) and is_video_file(filename):
			try:
				found.append(parse_filename(filename))
			except FileIOException as e:
				log.error(f'{filename}: {repr(e)}', prefix='Error')
	return found


def is_video_file(filename: str) -> bool:
	"""
	Returns True if the file has an extension indicating it's a video file
	"""
	parts = filename.rsplit('.', 1)
	if len(parts) == 1:
		return False
	return parts[1].lower() in {'mp4', 'flv', 'avi', 'mkv', 'm4v'}


def parse_filename(filename: str) -> dict[str, str | int]:
	"""
	Uses regex to pull series name, season and episode numbers
	"""
	regex_parsers = [
		# S##E## style, optional year: "Show.S01E01.mkv", "Show 2020 S01E01.mp4"
		r'^(?P<name>.*?)\.*?(\d{4})?\.*?s *(?P<s>\d+) *e *(?P<e>\d+).*\.(?P<ext>.*?)$',
		# Season x episode: "Show 1x01.mkv", "Show.12x05.avi"
		r'^(?P<name>.*?)(?P<s>\d+)x(?P<e>\d+).*\.(?P<ext>.*?)$',
		# Packed season+episode digits: "Show 101.mp4" → S1E01, "Show.1205.mkv" → S12E05
		r'^(?P<name>(?:.*?\D|))(?P<s>\d{1,2})(?P<e>\d{2})(?:\D.*|)\.(?P<ext>.*?)$',
	]
	for parser in regex_parsers:
		match = re.compile(parser, re.IGNORECASE).search(filename)
		if not match:
			continue
		match_dict = match.groupdict()
		return {
			'name': match_dict['name'].replace('.', ' ').strip(),
			'season': int(match_dict['s']),
			'episode': int(match_dict['e']),
			'filename': filename,
			'extension': match_dict['ext'],
		}

	raise FileIOException('Filename not matched.')


def prompt_user(orig_name: str, series_list: list[dict[str, Any]]) -> dict[str, Any] | None:
	"""
	Prompt user to select which show this episode is from
	"""
	for count, value in enumerate(series_list):
		if value['year'] is not None:
			log.plain('({}) {} ({})'.format(count + 1, value['name'], value['year']))
		else:
			log.plain('({}) {}'.format(count + 1, value['name']))
	choice = input(log.prompt(f'Select correct series for {orig_name} ("i" to ignore): '))
	if choice == '':
		return series_list[0]
	if choice == 'i':
		return None
	try:
		selection = int(choice)
	except ValueError as exc:
		raise FileIOException('Invalid input.') from exc
	if selection < 1 or selection > len(series_list):
		raise FileIOException('Invalid input.')
	return series_list[selection - 1]


def winsafe_filename(filename: str) -> str:
	"""
	Make a windows-safe filename
	"""
	return re.sub(r'[\\/:"*?<>|]+', '', filename)


def get_filename(filename: str, season: int, episode: int, episodename: str, extension: str) -> str:
	"""
	Returns the new filename to use.
	"""
	season_str = f'{season:02d}'
	episode_str = f'{episode:02d}'
	new_filename = f'S{season_str}E{episode_str} - {episodename}.{extension}'
	log.info(filename, prefix='Current')
	log.info(new_filename, prefix='New')
	return winsafe_filename(new_filename)


def move_file(from_path: str, to_path: str) -> None:
	"""
	Move a file with O_EXCL destination reservation and cross-device fallback.
	"""
	try:
		fd = os.open(to_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
		os.close(fd)
	except FileExistsError as exc:
		raise FileIOException(f'{to_path} already Exists.') from exc

	try:
		os.replace(from_path, to_path)
	except OSError:
		# Cross-device: replace reserved dest with content, then remove source.
		try:
			shutil.copy2(from_path, to_path)
			os.unlink(from_path)
		except OSError as exc:
			with contextlib.suppress(OSError):
				os.unlink(to_path)
			raise FileIOException(f'Failed to move {from_path} -> {to_path}: {exc}') from exc


def remove_empty_parents(path: str, stop_at: str | None = None) -> None:
	"""
	Remove empty parent directories of path up to (but not including) stop_at.
	"""
	parent = os.path.dirname(path)
	stop = os.path.abspath(stop_at) if stop_at else None
	while parent and parent != os.path.dirname(parent):
		if stop and os.path.abspath(parent) == stop:
			break
		try:
			os.rmdir(parent)
		except OSError:
			break
		parent = os.path.dirname(parent)


def rename_and_move(
	orig_directory: str,
	orig_filename: str,
	new_directory: str,
	new_filename: str,
	show: str,
	year: int | None,
	season: int,
) -> str:
	"""
	Rename and sort the file into folders.

	Returns the absolute destination path.
	"""
	safe_show = winsafe_filename(str(show))
	if not safe_show:
		raise FileIOException('Show name is empty after sanitization.')
	folder_name = f'{safe_show} ({year})' if year is not None else safe_show
	show_folder = os.path.join(new_directory, folder_name)
	season_folder = os.path.join(show_folder, f'Season {season}')

	os.makedirs(season_folder, exist_ok=True)

	curr_file = os.path.join(orig_directory, orig_filename)
	new_file = os.path.join(season_folder, new_filename)
	move_file(curr_file, new_file)

	log.success(new_file, prefix='Moved')
	return new_file
