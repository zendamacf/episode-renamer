import json

import pytest
from helpers import OFFICE

import series_cache


class TestSeriesCacheKeys:
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
