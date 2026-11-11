"""
Searches for tv show episode files, and renames & sorts, them
using information from TMDB
"""

import contextlib
import json
import os
import re
import shutil
from collections.abc import Callable
from enum import Enum
from typing import Any, TypedDict

import log


class SubtitleCompanion(TypedDict):
	filename: str
	extension: str
	lang: str | None


class Platform(Enum):
	plex = 'plex'
	jellyfin = 'jellyfin'
	emby = 'emby'
	kodi = 'kodi'


class PlatformTemplate(TypedDict):
	show_folder: str
	season_folder: str
	episode: str
	# Episode marker substituted into ``episode`` as ``{episode_label}``; a platform can
	# use a different range style (e.g. ``E01E02``) without touching the file template.
	episode_label: str
	episode_range_label: str


class FileIOException(Exception):
	pass


REQUIRED_CONFIG_KEYS = ('MOVIEDB_KEY', 'HOME', 'MOVED')
VIDEO_EXTENSIONS = frozenset({'mp4', 'flv', 'avi', 'mkv', 'm4v', 'ts', 'wmv', 'mov', 'webm'})
SUBTITLE_EXTENSIONS = frozenset({'srt', 'ass', 'ssa', 'vtt', 'sub'})
# Metadata and artwork that share the video's basename (e.g. ``stem.nfo``, ``stem.jpg``).
SIDECAR_EXTENSIONS = frozenset({'nfo', 'jpg', 'png'})
# Default language tag when the source subtitle has no language in its name.
DEFAULT_SUBTITLE_LANG = 'en'

DEFAULT_PLATFORM: Platform = Platform.plex
# Folder and file name templates per media server. ``episode`` has no extension;
# fields: show, year (folder only), season, episode_label, title. ``episode_label`` is
# built from ``episode_label`` / ``episode_range_label`` (fields: episode, episode_end).
PLATFORM_TEMPLATES: dict[Platform, PlatformTemplate] = {
	Platform.plex: {
		'show_folder': '{show} ({year})',
		'season_folder': 'Season {season}',
		'episode': 'S{season:02d}{episode_label} - {title}',
		'episode_label': 'E{episode:02d}',
		'episode_range_label': 'E{episode:02d}-E{episode_end:02d}',
	},
	Platform.jellyfin: {
		'show_folder': '{show} ({year})',
		'season_folder': 'Season {season:02d}',
		'episode': '{show} S{season:02d}{episode_label} - {title}',
		'episode_label': 'E{episode:02d}',
		'episode_range_label': 'E{episode:02d}-E{episode_end:02d}',
	},
	Platform.emby: {
		'show_folder': '{show} ({year})',
		'season_folder': 'Season {season:02d}',
		'episode': '{show} - S{season:02d}{episode_label} - {title}',
		'episode_label': 'E{episode:02d}',
		'episode_range_label': 'E{episode:02d}-E{episode_end:02d}',
	},
	Platform.kodi: {
		'show_folder': '{show} ({year})',
		'season_folder': 'Season {season:02d}',
		'episode': '{show} - S{season:02d}{episode_label} - {title}',
		'episode_label': 'E{episode:02d}',
		'episode_range_label': 'E{episode:02d}-E{episode_end:02d}',
	},
}


def _normalize_directory(path: str) -> str:
	return os.path.realpath(os.path.abspath(path))


def resolve_platform(platform: str | Platform | None) -> Platform:
	"""
	Return the matching ``Platform`` (default Plex when None), or raise for an unknown one.
	"""
	if platform is None:
		return DEFAULT_PLATFORM
	if isinstance(platform, Platform):
		return platform
	try:
		return Platform(str(platform).strip().lower())
	except ValueError:
		choices = ', '.join(p.value for p in Platform)
		raise FileIOException(f'Unknown platform {platform!r}. Choose one of: {choices}.') from None


def _validate_home_moved(home: str, moved: str) -> None:
	"""
	Reject dangerous HOME/MOVED combinations before any file operations.
	"""
	home_norm = _normalize_directory(home)
	moved_norm = _normalize_directory(moved)
	if home_norm == moved_norm:
		raise FileIOException(
			f'HOME and MOVED must be different directories (both resolve to {home_norm}).'
		)
	nested = home_norm.startswith(moved_norm + os.sep) or moved_norm.startswith(home_norm + os.sep)
	if nested:
		raise FileIOException(
			'HOME and MOVED must not nest inside each other '
			f'(HOME={home_norm}, MOVED={moved_norm}).'
		)


def read_config(filename: str) -> dict:
	"""
	Reads a JSON config file into a dict
	"""
	with open(filename) as file:
		config = json.load(file)

	missing = [k for k in REQUIRED_CONFIG_KEYS if not config.get(k)]
	if missing:
		raise FileIOException('Missing or empty config keys: {}'.format(', '.join(missing)))

	_validate_home_moved(config['HOME'], config['MOVED'])
	if 'PLATFORM' in config:
		config['PLATFORM'] = resolve_platform(config['PLATFORM']).value
	return config


def _append_video_file(
	found: list,
	directory: str,
	rel_path: str,
	filename: str,
) -> None:
	if not is_video_file(filename):
		return
	try:
		parsed = parse_filename(filename)
	except FileIOException as e:
		log.error(f'{rel_path}: {repr(e)}', prefix='Error')
		return
	parsed['rel_path'] = rel_path
	found.append(parsed)


def find_files(directory: str, *, recursive: bool = False) -> list:
	"""
	Gets a list of video files in a given directory.

	When ``recursive`` is True, scans nested folders under ``directory`` and sets
	``rel_path`` on each entry (relative to ``directory``).
	"""
	log.info(directory, prefix='Checking')
	found: list = []
	if recursive:
		for root, dirnames, filenames in os.walk(directory):
			dirnames.sort(key=str.lower)
			for filename in sorted(filenames, key=str.lower):
				abs_path = os.path.join(root, filename)
				if not os.path.isfile(abs_path):
					continue
				rel_path = os.path.relpath(abs_path, directory)
				_append_video_file(found, directory, rel_path, filename)
	else:
		for filename in sorted(os.listdir(directory), key=str.lower):
			if os.path.isfile(os.path.join(directory, filename)):
				_append_video_file(found, directory, filename, filename)
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


def find_subtitle_companions(directory: str, video_filename: str) -> list[SubtitleCompanion]:
	"""
	Find subtitle files that pair with a video by basename.

	Matches ``stem.srt`` and ``stem.<lang>.srt`` (case-insensitive lang/ext).
	"""
	stem = video_filename.rsplit('.', 1)[0]
	prefix = stem + '.'
	companions: list[SubtitleCompanion] = []
	for name in sorted(os.listdir(directory), key=str.lower):
		if name == video_filename or not name.startswith(prefix):
			continue
		path = os.path.join(directory, name)
		if not os.path.isfile(path):
			continue
		rest = name[len(prefix) :]
		parts = rest.split('.')
		if len(parts) == 1 and parts[0].lower() in SUBTITLE_EXTENSIONS:
			companions.append({'filename': name, 'extension': parts[0].lower(), 'lang': None})
		elif len(parts) == 2 and parts[0] and parts[1].lower() in SUBTITLE_EXTENSIONS:
			companions.append(
				{
					'filename': name,
					'extension': parts[1].lower(),
					'lang': parts[0].lower(),
				}
			)
	return companions


def find_sidecar_files(directory: str, video_filename: str) -> list[dict[str, str]]:
	"""
	Find ``.nfo`` and artwork (``.jpg``, ``.png``) files sharing the video's basename.

	Matches ``stem.<ext>`` only (case-insensitive ext).
	"""
	stem = video_filename.rsplit('.', 1)[0]
	prefix = stem + '.'
	sidecars: list[dict[str, str]] = []
	for name in sorted(os.listdir(directory), key=str.lower):
		if name == video_filename or not name.startswith(prefix):
			continue
		ext = name[len(prefix) :]
		if ext.lower() not in SIDECAR_EXTENSIONS:
			continue
		if not os.path.isfile(os.path.join(directory, name)):
			continue
		sidecars.append({'filename': name, 'extension': ext.lower()})
	return sidecars


def _episode_range_end(first: int, more: str | None) -> int | None:
	"""
	Last episode of a multi-episode marker (``E01E02E03``, ``E01-E03``), or None.

	Only an ascending range is accepted. A chain of three or more must be consecutive,
	since the whole span is named; otherwise the file is treated as a single episode.
	"""
	if not more:
		return None
	numbers = [first, *(int(n) for n in re.findall(r'\d+', more))]
	if numbers[-1] <= first:
		return None
	if len(numbers) > 2 and numbers != list(range(first, numbers[-1] + 1)):
		return None
	return numbers[-1]


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
		+ r'[\.\s]*s *(?P<s>\d+) *e *(?P<e>\d+)(?P<e_more>(?:[\.\s]*-?[\.\s]*e *\d+)*).*'
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
		episode = int(match_dict['e'])
		episode_end = _episode_range_end(episode, match_dict.get('e_more'))
		parsed: dict[str, str | int | None] = {
			'name': match_dict['name'].replace('.', ' ').strip().rstrip(' -'),
			'season': int(match_dict['s']),
			'episode': episode,
			'episode_end': episode_end,
			'year': int(year_raw) if year_raw else None,
			'filename': filename,
			'extension': match_dict['ext'],
		}
		if parser is regex_parsers[-1]:
			# "Show - 105" may be S1E05 or absolute episode 105.
			parsed['absolute'] = int(match_dict['s'] + match_dict['e'])
		return parsed

	raise FileIOException('Filename not matched.')


def _format_country(country: list[str] | None) -> str:
	if not country:
		return ''
	return f' [{", ".join(country)}]'


def prompt_user(
	orig_name: str,
	series_list: list[dict[str, Any]],
	*,
	can_fetch_more: Callable[[], bool] | None = None,
	fetch_more: Callable[[], list[dict[str, Any]]] | None = None,
) -> dict[str, Any] | None:
	"""
	Prompt user to select which show this episode is from.
	"""
	while True:
		for count, value in enumerate(series_list):
			country = _format_country(value.get('country'))
			if value['year'] is not None:
				log.plain('({}) {} ({}){}'.format(count + 1, value['name'], value['year'], country))
			else:
				log.plain('({}) {}{}'.format(count + 1, value['name'], country))
		extra = ', "n" for more results' if can_fetch_more and can_fetch_more() else ''
		choice = input(
			log.prompt(f'Select correct series for {orig_name} ("i" to ignore{extra}): ')
		)
		if choice == 'n':
			if fetch_more is None:
				raise FileIOException('Invalid input.')
			series_list = fetch_more()
			continue
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


def prompt_numbering(
	orig_name: str,
	choices: list[tuple[int, int, str]],
) -> tuple[int, int] | None:
	"""
	Ask which (season, episode) an ambiguous number refers to.
	"""
	for count, (season, episode, title) in enumerate(choices):
		log.plain(f'({count + 1}) S{season:02d}E{episode:02d} - {title}')
	choice = input(log.prompt(f'Select correct episode for {orig_name} ("i" to skip): '))
	if choice == '':
		return choices[0][:2]
	if choice == 'i':
		return None
	try:
		selection = int(choice)
	except ValueError as exc:
		raise FileIOException('Invalid input.') from exc
	if selection < 1 or selection > len(choices):
		raise FileIOException('Invalid input.')
	return choices[selection - 1][:2]


def winsafe_filename(filename: str) -> str:
	"""
	Make a windows-safe filename
	"""
	return re.sub(r'[\\/:"*?<>|]+', '', filename)


def _episode_basename(
	platform: Platform,
	show: str,
	season: int,
	episode: int,
	episodename: str,
	episode_end: int | None = None,
) -> str:
	template = PLATFORM_TEMPLATES[platform]
	if episode_end is None:
		label = template['episode_label'].format(episode=episode)
	else:
		label = template['episode_range_label'].format(episode=episode, episode_end=episode_end)
	return template['episode'].format(
		show=winsafe_filename(show), season=season, episode_label=label, title=episodename
	)


def get_filename(
	filename: str,
	season: int,
	episode: int,
	episodename: str,
	extension: str,
	*,
	show: str = '',
	platform: Platform = DEFAULT_PLATFORM,
	episode_end: int | None = None,
) -> str:
	"""
	Returns the new filename to use.
	"""
	base = _episode_basename(platform, show, season, episode, episodename, episode_end)
	new_filename = f'{base}.{extension}'
	log.info(filename, prefix='Current')
	log.info(new_filename, prefix='New')
	return winsafe_filename(new_filename)


def get_subtitle_filename(
	filename: str,
	season: int,
	episode: int,
	episodename: str,
	extension: str,
	lang: str = DEFAULT_SUBTITLE_LANG,
	*,
	show: str = '',
	platform: Platform = DEFAULT_PLATFORM,
	episode_end: int | None = None,
) -> str:
	"""
	Returns the new subtitle filename (episode name plus ``.<lang>.ext``).
	"""
	base = _episode_basename(platform, show, season, episode, episodename, episode_end)
	new_filename = f'{base}.{lang}.{extension}'
	log.info(filename, prefix='Current')
	log.info(new_filename, prefix='New')
	return winsafe_filename(new_filename)


def get_sidecar_filename(
	filename: str,
	season: int,
	episode: int,
	episodename: str,
	extension: str,
	*,
	show: str = '',
	platform: Platform = DEFAULT_PLATFORM,
	episode_end: int | None = None,
) -> str:
	"""
	Returns the new sidecar filename (episode name plus ``.ext``).
	"""
	return get_filename(
		filename,
		season,
		episode,
		episodename,
		extension,
		show=show,
		platform=platform,
		episode_end=episode_end,
	)


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
	platform: Platform = DEFAULT_PLATFORM,
) -> tuple[str, bool]:
	"""
	Rename and sort the file into folders.

	Returns ``(absolute destination path, moved)``. When the destination file
	already exists at the computed path, the move is skipped (``moved`` is False)
	so neither the destination nor the source is overwritten or deleted.
	"""
	safe_show = winsafe_filename(str(show))
	if not safe_show:
		raise FileIOException('Show name is empty after sanitization.')
	templates = PLATFORM_TEMPLATES[platform]
	folder_name = (
		templates['show_folder'].format(show=safe_show, year=year)
		if year is not None
		else safe_show
	)
	show_folder = os.path.join(new_directory, folder_name)
	season_folder = os.path.join(show_folder, templates['season_folder'].format(season=season))

	os.makedirs(season_folder, exist_ok=True)

	curr_file = os.path.join(orig_directory, orig_filename)
	new_file = os.path.join(season_folder, new_filename)
	if os.path.exists(new_file):
		if os.path.exists(curr_file):
			log.warn(f'{new_file} (source remains at {curr_file})', prefix='Already')
		else:
			log.success(new_file, prefix='Already')
		return new_file, False

	move_file(curr_file, new_file)

	log.success(new_file, prefix='Moved')
	return new_file, True
