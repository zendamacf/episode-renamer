import json

import pytest
from helpers import OFFICE

import series_cache


class TestSeriesCacheKeys:
	def test_empty_cache_structure(self):
		assert series_cache.empty_cache() == {'version': 1, 'entries': {}}

	def test_round_trip_cache_key(self):
		key = ('The Office', 2005)
		encoded = series_cache.serialize_cache_key(*key)
		assert series_cache.deserialize_cache_key(encoded) == key

	def test_round_trip_without_year(self):
		key = ('Mystery Show', None)
		encoded = series_cache.serialize_cache_key(*key)
		assert series_cache.deserialize_cache_key(encoded) == key


class TestCacheValidation:
	def test_deserialize_invalid_key_shape(self):
		with pytest.raises(series_cache.SeriesCacheException, match='Invalid series cache key'):
			series_cache.deserialize_cache_key('"not-a-list"')

	def test_deserialize_invalid_key_name_type(self):
		with pytest.raises(
			series_cache.SeriesCacheException,
			match='Invalid series cache key name',
		):
			series_cache.deserialize_cache_key('[1, 2005]')

	def test_deserialize_invalid_key_year_type(self):
		with pytest.raises(
			series_cache.SeriesCacheException,
			match='Invalid series cache key year',
		):
			series_cache.deserialize_cache_key('["Show", "2005"]')

	def test_normalize_series_entry_requires_id_and_name(self):
		with pytest.raises(series_cache.SeriesCacheException, match='integer id'):
			series_cache.normalize_series_entry({'name': 'Show'})
		with pytest.raises(series_cache.SeriesCacheException, match='non-empty name'):
			series_cache.normalize_series_entry({'id': 1, 'name': ''})


class TestLoadCache:
	def test_missing_file_returns_empty(self, isolate_series_cache):
		assert series_cache.load_cache() == {}
		assert not isolate_series_cache.exists()

	def test_loads_existing_entries(self, isolate_series_cache):
		payload = {
			'version': 1,
			'entries': {
				series_cache.serialize_cache_key('The Office', 2005): OFFICE,
			},
		}
		isolate_series_cache.write_text(json.dumps(payload))
		loaded = series_cache.load_cache()
		assert loaded == {('The Office', 2005): OFFICE}

	def test_invalid_json_raises(self, isolate_series_cache):
		isolate_series_cache.write_text('not-json')
		with pytest.raises(series_cache.SeriesCacheException, match='Failed to read'):
			series_cache.load_cache()

	def test_invalid_format_raises(self, isolate_series_cache):
		isolate_series_cache.write_text(json.dumps({'version': 1, 'entries': 'nope'}))
		with pytest.raises(series_cache.SeriesCacheException, match='Invalid'):
			series_cache.load_cache()

	def test_invalid_entry_raises(self, isolate_series_cache):
		isolate_series_cache.write_text(
			json.dumps(
				{
					'version': 1,
					'entries': {series_cache.serialize_cache_key('Show', None): 'not-a-dict'},
				}
			)
		)
		with pytest.raises(series_cache.SeriesCacheException, match='Invalid series cache entry'):
			series_cache.load_cache()


class TestSaveCache:
	def test_save_and_reload(self, isolate_series_cache):
		matches: dict[tuple[str, int | None], dict] = {}
		matches[('The Office', None)] = OFFICE
		series_cache.save_cache(matches)
		assert series_cache.load_cache() == matches
		data = json.loads(isolate_series_cache.read_text())
		assert data['version'] == 1
		assert len(data['entries']) == 1

	def test_save_replace_failure_raises(self, isolate_series_cache, monkeypatch):
		matches: dict[tuple[str, int | None], dict] = {}
		matches[('The Office', None)] = OFFICE

		def fail_replace(src, dst):
			raise OSError('disk full')

		monkeypatch.setattr(series_cache.os, 'replace', fail_replace)

		with pytest.raises(series_cache.SeriesCacheException, match='Failed to write'):
			series_cache.save_cache(matches)

		leftovers = list(isolate_series_cache.parent.glob('.series_cache_*'))
		assert leftovers == []

	def test_save_cleanup_ignores_unlink_errors(self, isolate_series_cache, monkeypatch):
		matches: dict[tuple[str, int | None], dict] = {}
		matches[('The Office', None)] = OFFICE

		def fail_replace(src, dst):
			raise OSError('disk full')

		def fail_unlink(path):
			raise OSError('busy')

		monkeypatch.setattr(series_cache.os, 'replace', fail_replace)
		monkeypatch.setattr(series_cache.os, 'unlink', fail_unlink)

		with pytest.raises(series_cache.SeriesCacheException, match='Failed to write'):
			series_cache.save_cache(matches)
