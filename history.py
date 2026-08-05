"""
Persistent rename journal for undo support.
"""

import json
import os
import tempfile
from datetime import datetime, timezone

HISTORY_PATH = 'rename_history.json'
MAX_BATCHES = 20
HISTORY_VERSION = 1


class HistoryException(Exception):
	pass


def empty_history() -> dict:
	return {'version': HISTORY_VERSION, 'batches': []}


def load_history(path: str | None = None) -> dict:
	"""
	Load rename history. Missing file returns an empty journal.
	"""
	if path is None:
		path = HISTORY_PATH
	if not os.path.exists(path):
		return empty_history()
	try:
		with open(path) as file:
			data = json.load(file)
	except (OSError, json.JSONDecodeError) as exc:
		raise HistoryException('Failed to read rename history {}: {}'.format(path, exc)) from exc
	if not isinstance(data, dict) or not isinstance(data.get('batches'), list):
		raise HistoryException('Invalid rename history format in {}'.format(path))
	return data


def save_history(data: dict, path: str | None = None) -> None:
	"""
	Atomically write rename history to disk.
	"""
	if path is None:
		path = HISTORY_PATH
	directory = os.path.dirname(os.path.abspath(path)) or '.'
	fd, tmp_path = tempfile.mkstemp(prefix='.rename_history_', dir=directory)
	try:
		with os.fdopen(fd, 'w') as file:
			json.dump(data, file, indent=2)
			file.write('\n')
		os.replace(tmp_path, path)
	except OSError as exc:
		try:
			os.unlink(tmp_path)
		except OSError:
			pass
		raise HistoryException('Failed to write rename history {}: {}'.format(path, exc)) from exc


def append_batch(moves: list, path: str | None = None) -> None:
	"""
	Append a batch of successful moves. Empty batches are ignored.
	Keeps only the most recent MAX_BATCHES batches.
	"""
	if not moves:
		return
	if path is None:
		path = HISTORY_PATH
	data = load_history(path)
	batch = {
		'id': datetime.now(timezone.utc).isoformat(),
		'moves': list(moves),
	}
	data['batches'].append(batch)
	data['batches'] = data['batches'][-MAX_BATCHES:]
	data['version'] = HISTORY_VERSION
	save_history(data, path)
