#!/usr/bin/env python3

import argparse
import os
from typing import Literal

import file_io as io
import history
import log
import moviedb

parser = argparse.ArgumentParser(prog='Episode Renamer')
parser.add_argument(
	'--dryrun',
	action='store_true',
	help='Instead of renaming the files, just display what changes would be made.'
)
parser.add_argument(
	'--undo',
	nargs='?',
	const=1,
	type=int,
	metavar='N',
	help='Undo the last N rename batch(es) (default: 1).'
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
) -> dict | Literal['skipped']:
	"""
	Resolve metadata and optionally rename one file.

	Returns a move record {'src', 'dest'} on success, or 'skipped'.
	Raises on hard failures so the caller can isolate the error and continue
	the batch.
	"""
	if f['name'] in matches:
		chosen = matches[f['name']]
		log.info(
			f"{_series_label(chosen)} for {f['name']}",
			prefix='Cached',
		)
	else:
		series_list = moviedb.get_series(f['name'], config['MOVIEDB_KEY'])
		if not series_list:
			log.warn(f['name'], prefix='No match')
			return 'skipped'

		if len(series_list) == 1:
			chosen = series_list[0]
			log.info(
				f"{_series_label(chosen)} for {f['name']}",
				prefix='Matched',
			)
		else:
			chosen = io.prompt_user(f['name'], series_list)
			if chosen is None:
				log.warn(f['name'], prefix='Ignoring')
				return 'skipped'
			log.info(
				f"{_series_label(chosen)} for {f['name']}",
				prefix='Selected',
			)

		matches[f['name']] = chosen

	episodename = moviedb.get_episode(
		chosen['id'],
		f['season'],
		f['episode'],
		config['MOVIEDB_KEY']
	)
	if episodename is None:
		log.warn(
			f"{f['name']} S{f['season']}E{f['episode']}",
			prefix='No episode',
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
			f'{f["filename"]} -> {new_filename}',
			prefix='Dry-run',
		)
		return 'skipped'

	src = os.path.join(config['HOME'], f['filename'])
	dest = io.rename_and_move(
		config['HOME'],
		f['filename'],
		config['MOVED'],
		new_filename,
		chosen['name'],
		chosen['year'],
		f['season']
	)
	return {'src': src, 'dest': dest}


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

	config = io.read_config('config.json')
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
			f"{batch['id']} ({len(batch['moves'])} file(s))",
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
			updated_tail.append({
				'id': batch['id'],
				'moves': list(reversed(failed_moves)),
			})

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
	if failed:
		log.warn(summary, prefix='Undone')
	else:
		log.info(summary, prefix='Undone')


def main(dryrun: bool) -> None:
	"""
	Main rename function
	"""
	log.info('Running renamer...')
	if dryrun:
		log.warn('No files will be moved', prefix='Dry-run')

	config = io.read_config('config.json')
	env_key = os.environ.get('MOVIEDB_KEY')
	if env_key:
		config['MOVIEDB_KEY'] = env_key
		log.info('MOVIEDB_KEY from environment', prefix='Using')

	found = io.find_files(config['HOME'])
	if len(found) == 0:
		log.warn('No files found', prefix='Skip')
		return

	log.info(f'{len(found)} file(s)', prefix='Found')

	matches = {}
	moves = []
	moved = 0
	skipped = 0
	failed = 0

	for f in found:
		try:
			result = _process_file(f, config, matches, dryrun)
		except (moviedb.MovieDBException, io.FileIOException, OSError) as e:
			log.error(f"{f['filename']}: {e}", prefix='Failed')
			failed += 1
			continue

		if result == 'skipped':
			skipped += 1
		else:
			moves.append(result)
			moved += 1

	if moves and not dryrun:
		try:
			history.append_batch(moves)
		except history.HistoryException as e:
			log.error(str(e), prefix='History')

	summary = f'{moved} moved, {skipped} skipped, {failed} failed'
	if failed:
		log.warn(summary, prefix='Done')
	else:
		log.info(summary, prefix='Done')


if __name__ == '__main__':
	args = parser.parse_args()
	if args.undo is not None:
		undo_batches(args.undo, args.dryrun)
	else:
		main(args.dryrun)
