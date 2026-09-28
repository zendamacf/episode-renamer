"""
Persistent TMDB series selection cache between runs.
"""

import contextlib
import json
import os
import tempfile

SERIES_CACHE_PATH = 'series_cache.json'
CACHE_VERSION = 1

_SERIES_FIELDS = ('id', 'name', 'year', 'country')


class SeriesCacheException(Exception):
	pass


def empty_cache() -> dict:
	return {'version': CACHE_VERSION, 'entries': {}}


def serialize_cache_key(name: str, year: int | None) -> str:
	return json.dumps([name, year], ensure_ascii=False)


def deserialize_cache_key(key: str) -> tuple[str, int | None]:
	decoded = json.loads(key)
	if not isinstance(decoded, list) or len(decoded) != 2:
		raise SeriesCacheException(f'Invalid series cache key: {key!r}')
	name, year = decoded
	if not isinstance(name, str):
		raise SeriesCacheException(f'Invalid series cache key name: {key!r}')
	if year is not None and not isinstance(year, int):
		raise SeriesCacheException(f'Invalid series cache key year: {key!r}')
	return (name, year)


def normalize_series_entry(series: dict) -> dict:
	entry = {field: series.get(field) for field in _SERIES_FIELDS}
	if not isinstance(entry['id'], int):
		raise SeriesCacheException('Series cache entry requires integer id')
	if not isinstance(entry['name'], str) or not entry['name']:
		raise SeriesCacheException('Series cache entry requires non-empty name')
	return entry


def load_cache(path: str | None = None) -> dict[tuple[str, int | None], dict]:
	"""
	Load cached series selections. Missing file returns an empty cache.
	"""
	if path is None:
		path = SERIES_CACHE_PATH
	if not os.path.exists(path):
		return {}
	try:
		with open(path) as file:
			data = json.load(file)
	except (OSError, json.JSONDecodeError) as exc:
		raise SeriesCacheException(f'Failed to read series cache {path}: {exc}') from exc
	if not isinstance(data, dict) or not isinstance(data.get('entries'), dict):
		raise SeriesCacheException(f'Invalid series cache format in {path}')
	loaded: dict[tuple[str, int | None], dict] = {}
	for key, value in data['entries'].items():
		if not isinstance(key, str) or not isinstance(value, dict):
			raise SeriesCacheException(f'Invalid series cache entry in {path}')
		cache_key = deserialize_cache_key(key)
		loaded[cache_key] = normalize_series_entry(value)
	return loaded


def save_cache(
	matches: dict[tuple[str, int | None], dict],
	path: str | None = None,
) -> None:
	"""
	Atomically write series selections to disk.
	"""
	if path is None:
		path = SERIES_CACHE_PATH
	payload = {
		'version': CACHE_VERSION,
		'entries': {
			serialize_cache_key(name, year): normalize_series_entry(series)
			for (name, year), series in matches.items()
		},
	}
	directory = os.path.dirname(os.path.abspath(path)) or '.'
	fd, tmp_path = tempfile.mkstemp(prefix='.series_cache_', dir=directory)
	try:
		with os.fdopen(fd, 'w') as file:
			json.dump(payload, file, indent=2)
			file.write('\n')
		os.replace(tmp_path, path)
	except OSError as exc:
		with contextlib.suppress(OSError):
			os.unlink(tmp_path)
		raise SeriesCacheException(f'Failed to write series cache {path}: {exc}') from exc
