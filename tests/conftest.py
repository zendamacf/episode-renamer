import json

from unittest.mock import Mock

import pytest


SAMPLE_CONFIG = {
	'MOVIEDB_KEY': 'test-api-key',
	'HOME': '/tmp/home',
	'MOVED': '/tmp/moved',
}


@pytest.fixture
def sample_config():
	return SAMPLE_CONFIG.copy()


@pytest.fixture
def config_file(tmp_path, sample_config):
	path = tmp_path / 'config.json'
	path.write_text(json.dumps(sample_config))
	return path


@pytest.fixture
def mock_http_response():
	def _make(status_code, body=None, text=None):
		response = Mock()
		response.status_code = status_code
		if text is None and body is not None:
			text = json.dumps(body)
		response.text = text or ''
		return response
	return _make


@pytest.fixture
def tmdb_search_response():
	return {
		'results': [
			{'id': 2316, 'name': 'The Office', 'first_air_date': '2005-03-24'},
			{
				'id': 9999,
				'name': 'The Office (2010)',
				'first_air_date': '2010-01-01',
			},
		],
	}


@pytest.fixture
def tmdb_episode_response():
	return {'name': 'Pilot'}


@pytest.fixture
def series_list():
	return [
		{'id': 1, 'name': 'The Office', 'year': 2005},
		{'id': 2, 'name': 'The Office', 'year': 2010},
	]
