#!/usr/bin/env python3

import argparse
import os
import sys
from typing import Literal, TypedDict

import file_io as io
import history
import log
import moviedb
import series_cache

parser = argparse.ArgumentParser(prog='Episode Renamer')
parser.add_argument(
	'--dryrun',
	action='store_true',
	help='Instead of renaming the files, just display what changes would be made.',
)
parser.add_argument(
	'--quiet',
	action='store_true',
	help='Print errors and final summary only (for scripts and cron).',
)
parser.add_argument(
	'--recursive',
	action='store_true',
	help='Scan nested folders under HOME (overrides config RECURSIVE_SCAN).',
)
parser.add_argument(
	'--auto',
	nargs='?',
	const='first',
	choices=('first', 'skip'),
	metavar='{first,skip}',
	help='Never prompt (for cron/scripts). When several TMDB series match, use the top '
	'result (first, default) or skip the file (skip). Exits non-zero if a file is skipped '
	'or fails.',
)
parser.add_argument(
	'--platform',
	type=str.lower,
	choices=tuple(p.value for p in io.Platform),
	help='Media server naming layout (overrides config PLATFORM; default: plex).',
)
mode = parser.add_mutually_exclusive_group()
mode.add_argument(
	'--undo',
	nargs='?',
	const=1,
	type=int,
	metavar='N',
	help='Undo the last N rename batch(es) (default: 1).',
)
mode.add_argument(
	'--history',
	action='store_true',
	help='List recorded rename batches (newest last).',
)


class Config(TypedDict):
	HOME: str
	MOVED: str
	MOVIEDB_KEY: str
	SUBTITLE_LANG: str
	PLATFORM: io.Platform
	RECURSIVE_SCAN: bool


_CONFIG_PATH = 'config.json'
_CONFIG_HINT = (
	f'{_CONFIG_PATH} not found. Copy config-example.json to {_CONFIG_PATH} '
	'and set HOME, MOVED, and MOVIEDB_KEY. '
	'You can set MOVIEDB_KEY in the environment, but HOME and MOVED still come from config.'
)


def _load_config() -> Config | None:
	"""
	Load config.json for rename/undo. Returns None after logging a user-facing error.
	"""
	try:
		raw = io.read_config(_CONFIG_PATH)
		platform = io.resolve_platform(raw.get('PLATFORM'))
	except FileNotFoundError:
		log.error(_CONFIG_HINT, prefix='Error')
		return None
	except io.FileIOException as e:
		log.error(str(e), prefix='Error')
		return None

	config: Config = {
		'HOME': raw['HOME'],
		'MOVED': raw['MOVED'],
		'MOVIEDB_KEY': raw['MOVIEDB_KEY'],
		'SUBTITLE_LANG': raw.get('SUBTITLE_LANG') or io.DEFAULT_SUBTITLE_LANG,
		'PLATFORM': platform,
		'RECURSIVE_SCAN': bool(raw.get('RECURSIVE_SCAN')),
	}

	env_key = os.environ.get('MOVIEDB_KEY')
	if env_key:
		config['MOVIEDB_KEY'] = env_key
		log.info('MOVIEDB_KEY from environment', prefix='Using')

	env_lang = os.environ.get('SUBTITLE_LANG')
	if env_lang:
		config['SUBTITLE_LANG'] = env_lang
	return config


def _source_directory(home: str, rel_path: str) -> str:
	parent = os.path.dirname(rel_path)
	if not parent:
		return home
	return os.path.join(home, parent)


def _video_basename(rel_path: str) -> str:
	return os.path.basename(rel_path)


def _series_label(series: dict) -> str:
	if series.get('year') is not None:
		return f'{series["name"]} ({series["year"]})'
	return series['name']


def _series_cache_key(parsed: dict) -> tuple:
	return (parsed['name'], parsed.get('year'))


def _find_series_by_id(series_id: int, series_list: list) -> dict | None:
	for series in series_list:
		if series['id'] == series_id:
			return series
	return None


def _lookup_cached_series(name: str, apikey: str, series_id: int) -> tuple[dict | None, bool]:
	"""
	Return (series, had_results). Loads TMDB pages up to the search cap.
	"""
	session = moviedb.begin_series_search(name, apikey)
	if not session.results:
		return None, False
	while True:
		found = _find_series_by_id(series_id, session.results)
		if found is not None:
			return found, True
		if not moviedb.fetch_next_page(session):
			break
	return None, True


def _narrow_series_by_year(series_list: list, year: int | None) -> list:
	"""
	If a filename year is present, prefer TMDB results with that air year.

	Falls back to the full list when nothing matches the year so the user can
	still choose manually.
	"""
	if year is None:
		return series_list
	matched = [series for series in series_list if series.get('year') == year]
	if matched:
		return matched
	log.warn(f'no TMDB result for year {year}', prefix='Year')
	return series_list


def _resolve_numbering(
	f: dict, series: dict, config: Config, auto: str | None
) -> tuple[int, int, str | None] | None:
	"""
	Return (season, episode, TMDB title) for a parsed file, or None to skip it.

	A bare number like ``Show - 105`` is read as S1E05 unless the series has a TMDB
	absolute-order episode group that maps 105 elsewhere; then the user chooses.
	"""
	key = config['MOVIEDB_KEY']
	season, episode = f['season'], f['episode']
	title = moviedb.get_episode(series['id'], season, episode, key)
	absolute = f.get('absolute')
	if absolute is None:
		return season, episode, title
	mapped = moviedb.get_absolute_episode(series['id'], absolute, key)
	if mapped is None or mapped == (season, episode):
		return season, episode, title
	mapped_title = moviedb.get_episode(series['id'], mapped[0], mapped[1], key)
	if mapped_title is None:
		return season, episode, title
	if title is None:
		return mapped[0], mapped[1], mapped_title
	if auto == 'first':
		log.info(f'{f["rel_path"]}: S{season:02d}E{episode:02d}', prefix='Auto')
		return season, episode, title
	if auto == 'skip':
		log.warn(
			f'{f["rel_path"]}: absolute {absolute} or S{season:02d}E{episode:02d}',
			prefix='Ambiguous',
		)
		return None
	choice = io.prompt_numbering(
		f['rel_path'], [(season, episode, title), (mapped[0], mapped[1], mapped_title)]
	)
	if choice is None:
		log.warn(f['rel_path'], prefix='Ignoring')
		return None
	if choice == mapped:
		return mapped[0], mapped[1], mapped_title
	return season, episode, title


def _process_file(
	f: dict,
	config: Config,
	matches: dict,
	session_resolved: set[tuple],
	dryrun: bool,
	auto: str | None = None,
) -> list[dict] | Literal['skipped', 'previewed']:
	"""
	Resolve metadata and optionally rename one video (plus subtitle and sidecar files).

	Returns a list of move records ``{'src', 'dest'}`` on success, 'previewed' for a
	dry-run, or 'skipped'. ``auto`` is None (prompt) or 'first' / 'skip' (never prompt).
	Raises on hard failures so the caller can isolate the error and continue
	the batch.
	"""
	cache_key = _series_cache_key(f)
	chosen = None
	if cache_key in matches:
		if cache_key in session_resolved:
			chosen = matches[cache_key]
			log.info(
				f'{_series_label(chosen)} for {f["name"]}',
				prefix='Cached',
			)
		else:
			refreshed, had_results = _lookup_cached_series(
				f['name'],
				config['MOVIEDB_KEY'],
				matches[cache_key]['id'],
			)
			if not had_results:
				log.warn(f['name'], prefix='No match')
				return 'skipped'
			if refreshed is not None:
				matches[cache_key] = refreshed
				session_resolved.add(cache_key)
				chosen = refreshed
				log.info(
					f'{_series_label(chosen)} for {f["name"]}',
					prefix='Cached',
				)
			else:
				log.warn(
					f'cached TMDB id {matches[cache_key]["id"]} not in results for {f["name"]}',
					prefix='Cache',
				)
				del matches[cache_key]

	if chosen is None:
		session = moviedb.begin_series_search(f['name'], config['MOVIEDB_KEY'])
		if not session.results:
			log.warn(f['name'], prefix='No match')
			return 'skipped'

		series_list = _narrow_series_by_year(session.results, f.get('year'))

		if len(series_list) == 1:
			chosen = series_list[0]
			log.info(
				f'{_series_label(chosen)} for {f["name"]}',
				prefix='Matched',
			)
		elif auto == 'first':
			chosen = series_list[0]
			log.info(
				f'{_series_label(chosen)} for {f["name"]} ({len(series_list)} matches)',
				prefix='Auto',
			)
		elif auto == 'skip':
			log.warn(f'{f["rel_path"]}: {len(series_list)} matches', prefix='Ambiguous')
			return 'skipped'
		else:

			def _more_results() -> list:
				moviedb.fetch_next_page(session)
				return _narrow_series_by_year(session.results, f.get('year'))

			chosen = io.prompt_user(
				f['name'],
				series_list,
				can_fetch_more=lambda: moviedb.can_fetch_more(session),
				fetch_more=_more_results,
			)
			if chosen is None:
				log.warn(f['name'], prefix='Ignoring')
				return 'skipped'
			log.info(
				f'{_series_label(chosen)} for {f["name"]}',
				prefix='Selected',
			)

		matches[cache_key] = chosen
		session_resolved.add(cache_key)

	numbering = _resolve_numbering(f, chosen, config, auto)
	if numbering is None:
		return 'skipped'
	season, episode, episodename = numbering
	if episodename is None:
		log.warn(
			f'{f["name"]} S{season}E{episode}',
			prefix='No episode',
		)
		return 'skipped'

	platform = config['PLATFORM']
	show_name = chosen['name']
	new_filename = io.get_filename(
		f['filename'],
		season,
		episode,
		episodename,
		f['extension'],
		show=show_name,
		platform=platform,
	)
	video_rel = f['rel_path']
	source_dir = _source_directory(config['HOME'], video_rel)
	video_name = _video_basename(video_rel)
	default_sub_lang = config['SUBTITLE_LANG']
	companions = io.find_subtitle_companions(source_dir, video_name)
	subtitle_plans = [
		(
			sub['filename'],
			io.get_subtitle_filename(
				sub['filename'],
				season,
				episode,
				episodename,
				sub['extension'],
				lang=sub.get('lang') or default_sub_lang,
				show=show_name,
				platform=platform,
			),
		)
		for sub in companions
	]
	subtitle_plans += [
		(
			side['filename'],
			io.get_sidecar_filename(
				side['filename'],
				f['season'],
				f['episode'],
				episodename,
				side['extension'],
				show=show_name,
				platform=platform,
			),
		)
		for side in io.find_sidecar_files(source_dir, video_name)
	]

	if dryrun:
		log.warn(
			f'{video_rel} -> {new_filename}',
			prefix='Dry-run',
		)
		for sub_name, sub_new in subtitle_plans:
			log.warn(
				f'{sub_name} -> {sub_new}',
				prefix='Dry-run',
			)
		return 'previewed'

	moves: list[dict] = []
	src = os.path.join(config['HOME'], video_rel)
	dest, moved_video = io.rename_and_move(
		source_dir,
		video_name,
		config['MOVED'],
		new_filename,
		chosen['name'],
		chosen['year'],
		season,
		platform,
	)
	if moved_video:
		moves.append({'src': src, 'dest': dest})

	for sub_name, sub_new in subtitle_plans:
		try:
			sub_src = os.path.join(source_dir, sub_name)
			sub_dest, moved_sub = io.rename_and_move(
				source_dir,
				sub_name,
				config['MOVED'],
				sub_new,
				chosen['name'],
				chosen['year'],
				season,
				platform,
			)
			if moved_sub:
				moves.append({'src': sub_src, 'dest': sub_dest})
		except (io.FileIOException, OSError) as e:
			# Video already moved; keep going so successful moves are journaled.
			log.error(f'{sub_name}: {e}', prefix='Failed')

	return moves


def _restore_move(move: dict, dryrun: bool, moved_root: str) -> bool:
	"""
	Restore one recorded move. Returns True on success.
	"""
	src = move['src']
	dest = move['dest']
	if dryrun:
		log.warn(f'{dest} -> {src}', prefix='Dry-run')
		return True

	if not os.path.exists(dest):
		log.error(f'destination missing: {dest}', prefix='Cannot')
		return False
	if os.path.exists(src):
		log.error(f'original path occupied: {src}', prefix='Cannot')
		return False

	try:
		os.makedirs(os.path.dirname(src) or '.', exist_ok=True)
		io.move_file(dest, src)
	except (io.FileIOException, OSError) as e:
		log.error(f'{dest} -> {src}: {e}', prefix='Failed')
		return False

	io.remove_empty_parents(dest, stop_at=moved_root)
	log.success(src, prefix='Restored')
	return True


def show_history() -> None:
	"""
	Print recorded rename batches (oldest first, newest last).
	"""
	try:
		data = history.load_history()
	except history.HistoryException as e:
		log.error(str(e), prefix='Error')
		return

	batches = data['batches']
	if not batches:
		log.warn('No rename history', prefix='Skip')
		return

	log.info(f'{len(batches)} batch(es)', prefix='History')
	for index, batch in enumerate(batches, start=1):
		moves = batch.get('moves') or []
		# Newest batch is last; show relative undo index (1 = last undo).
		undo_index = len(batches) - index + 1
		log.info(
			f'{batch.get("id", "?")} ({len(moves)} file(s), undo {undo_index})',
			prefix='Batch',
		)
		for move in moves:
			src = move.get('src', '?')
			dest = move.get('dest', '?')
			log.plain(f'  {src} -> {dest}')


def undo_batches(n: int, dryrun: bool) -> None:
	"""
	Undo the last n rename batches (newest first).
	"""
	if n < 1:
		log.error('Undo count must be at least 1', prefix='Error')
		return

	log.info(f'last {n} batch(es)...', prefix='Undoing')
	if dryrun:
		log.warn('No files will be moved', prefix='Dry-run')

	config = _load_config()
	if config is None:
		return

	try:
		data = history.load_history()
	except history.HistoryException as e:
		log.error(str(e), prefix='Error')
		return

	batches = data['batches']
	if not batches:
		log.warn('No rename history to undo', prefix='Skip')
		return

	if n > len(batches):
		log.warn(
			f'Requested {n} batch(es) but only {len(batches)} available',
			prefix='Warn',
		)
		n = len(batches)

	to_undo = batches[-n:]
	kept_prefix = batches[:-n]
	updated_tail = []
	restored = 0
	failed = 0

	for batch in reversed(to_undo):
		log.info(
			f'{batch["id"]} ({len(batch["moves"])} file(s))',
			prefix='Batch',
		)
		failed_moves = []
		for move in reversed(batch['moves']):
			if _restore_move(move, dryrun, config['MOVED']):
				restored += 1
			else:
				failed += 1
				failed_moves.append(move)
		if not dryrun and failed_moves:
			updated_tail.append(
				{
					'id': batch['id'],
					'moves': list(reversed(failed_moves)),
				}
			)

	# updated_tail was built newest-first; restore oldest-first order
	updated_tail.reverse()

	if not dryrun:
		data['batches'] = kept_prefix + updated_tail
		try:
			history.save_history(data)
		except history.HistoryException as e:
			log.error(str(e), prefix='Error')
			return

	summary = f'{restored} restored, {failed} failed'
	log.summary(summary, prefix='Undone', tone='warn' if failed else 'info')


def main(
	dryrun: bool,
	recursive: bool = False,
	auto: str | None = None,
	platform: str | io.Platform | None = None,
) -> int:
	"""
	Main rename function. Returns the process exit code: non-zero only with ``auto``
	when a file was skipped or failed (or setup failed).
	"""
	failure_code = 1 if auto else 0
	log.info('Running renamer...')
	if dryrun:
		log.warn('No files will be moved', prefix='Dry-run')

	config = _load_config()
	if config is None:
		return failure_code

	try:
		if platform is not None:
			config['PLATFORM'] = io.resolve_platform(platform)
	except io.FileIOException as e:
		log.error(str(e), prefix='Error')
		return failure_code

	scan_recursive = recursive or config['RECURSIVE_SCAN']
	found = io.find_files(config['HOME'], recursive=scan_recursive)
	if len(found) == 0:
		log.warn('No files found', prefix='Skip')
		return 0

	log.info(f'{len(found)} file(s)', prefix='Found')

	try:
		matches = series_cache.load_cache()
	except series_cache.SeriesCacheException as e:
		log.error(str(e), prefix='Cache')
		matches = {}
	session_resolved: set[tuple] = set()
	moves = []
	moved = 0
	skipped = 0
	unresolved = 0
	failed = 0

	for f in found:
		try:
			result = _process_file(f, config, matches, session_resolved, dryrun, auto)
		except (moviedb.MovieDBException, io.FileIOException, OSError) as e:
			log.error(f'{f["rel_path"]}: {e}', prefix='Failed')
			failed += 1
			continue

		if result == 'skipped':
			skipped += 1
			unresolved += 1
		elif result == 'previewed':
			skipped += 1
		else:
			moves.extend(result)
			moved += len(result)

	if moves and not dryrun:
		try:
			history.append_batch(moves)
		except history.HistoryException as e:
			log.error(str(e), prefix='History')

	try:
		series_cache.save_cache(matches)
	except series_cache.SeriesCacheException as e:
		log.error(str(e), prefix='Cache')

	summary = f'{moved} moved, {skipped} skipped, {failed} failed'
	log.summary(summary, prefix='Done', tone='warn' if failed else 'info')
	return 1 if auto and (unresolved or failed) else 0


if __name__ == '__main__':
	args = parser.parse_args()
	log.set_quiet(args.quiet)
	if args.history:
		show_history()
	elif args.undo is not None:
		undo_batches(args.undo, args.dryrun)
	else:
		sys.exit(
			main(args.dryrun, recursive=args.recursive, auto=args.auto, platform=args.platform)
		)
