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
VIDEO_EXTENSIONS = frozenset({'mp4', 'flv', 'avi', 'mkv', 'm4v'})
SUBTITLE_EXTENSIONS = frozenset({'srt', 'ass', 'ssa', 'vtt', 'sub'})
# Language tag written on renamed subtitle files (e.g. S01E01 - Pilot.en.srt).
SUBTITLE_LANG = 'en'


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
	return parts[1].lower() in VIDEO_EXTENSIONS


def is_subtitle_file(filename: str) -> bool:
	"""
	Returns True if the file has a known subtitle extension.
	"""
	parts = filename.rsplit('.', 1)
	if len(parts) == 1:
		return False
	return parts[1].lower() in SUBTITLE_EXTENSIONS


def find_subtitle_companions(directory: str, video_filename: str) -> list[dict[str, str]]:
	"""
	Find subtitle files that pair with a video by basename.

	Matches ``stem.srt`` and ``stem.<lang>.srt`` (case-insensitive lang/ext).
	"""
	stem = video_filename.rsplit('.', 1)[0]
	prefix = stem + '.'
	companions: list[dict[str, str]] = []
	for name in sorted(os.listdir(directory), key=str.lower):
		if name == video_filename or not name.startswith(prefix):
			continue
		path = os.path.join(directory, name)
		if not os.path.isfile(path):
			continue
		rest = name[len(prefix) :]
		parts = rest.split('.')
		if len(parts) == 1 and parts[0].lower() in SUBTITLE_EXTENSIONS:
			companions.append({'filename': name, 'extension': parts[0].lower()})
		elif len(parts) == 2 and parts[0] and parts[1].lower() in SUBTITLE_EXTENSIONS:
			companions.append({'filename': name, 'extension': parts[1].lower()})
	return companions


def parse_filename(filename: str) -> dict[str, str | int | None]:
	"""
	Uses regex to pull series name, season and episode numbers.

	When present, a year between the series name and season/episode marker
	(e.g. ``Show 2005 S01E01`` or ``Show.(2005).1x01``) is returned as ``year``.
	"""
	# Anime releases sometimes prefix filenames with the encoder/group name in square brackets
	encoder_prefix = r'(?:\[[^\]]+\]\s*)?'
	file_start = r'^' + encoder_prefix
	file_end = r'\.(?P<ext>.*?)$'
	# Optional year as YYYY or (YYYY)
	optional_year = r'(?:[\.\s]+\(?(?P<year>\d{4})\)?)?'
	regex_parsers = [
		# S##E## style: "Show.S01E01.mkv", "Show 2020 S01E01.mp4", "Show.(2005).S01E01.mkv"
		file_start
		+ r'(?P<name>.*?)'
		+ optional_year
		+ r'[\.\s]*s *(?P<s>\d+) *e *(?P<e>\d+).*'
		+ file_end,
		# Season x episode: "Show 1x01.mkv", "Show.2005.12x05.avi"
		file_start
		+ r'(?P<name>.*?)'
		+ optional_year
		+ r'[\.\s]*(?P<s>\d+)x(?P<e>\d+).*'
		+ file_end,
		# Packed season+episode digits: "Show 101.mp4" → S1E01, "Show.1205.mkv" → S12E05
		file_start + r'(?P<name>(?:.*?\D|))(?P<s>\d{1,2})(?P<e>\d{2})(?:\D.*|)' + file_end,
	]
	for parser in regex_parsers:
		match = re.compile(parser, re.IGNORECASE).search(filename)
		if not match:
			continue
		match_dict = match.groupdict()
		year_raw = match_dict.get('year')
		return {
			'name': match_dict['name'].replace('.', ' ').strip().rstrip(' -'),
			'season': int(match_dict['s']),
			'episode': int(match_dict['e']),
			'year': int(year_raw) if year_raw else None,
			'filename': filename,
			'extension': match_dict['ext'],
		}

	raise FileIOException('Filename not matched.')


def _format_country(country: list[str] | None) -> str:
	if not country:
		return ''
	return f' [{", ".join(country)}]'


def prompt_user(orig_name: str, series_list: list[dict[str, Any]]) -> dict[str, Any] | None:
	"""
	Prompt user to select which show this episode is from
	"""
	for count, value in enumerate(series_list):
		country = _format_country(value.get('country'))
		if value['year'] is not None:
			log.plain('({}) {} ({}){}'.format(count + 1, value['name'], value['year'], country))
		else:
			log.plain('({}) {}{}'.format(count + 1, value['name'], country))
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


def get_subtitle_filename(
	filename: str,
	season: int,
	episode: int,
	episodename: str,
	extension: str,
) -> str:
	"""
	Returns the new subtitle filename (``SxxExx - Title.en.ext``).
	"""
	season_str = f'{season:02d}'
	episode_str = f'{episode:02d}'
	new_filename = f'S{season_str}E{episode_str} - {episodename}.{SUBTITLE_LANG}.{extension}'
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
