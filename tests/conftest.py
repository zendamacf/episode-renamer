import json

from unittest.mock import Mock

import pytest

from helpers import TMDB_EPISODE_RESPONSE, TMDB_SEARCH_RESPONSE

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
	def _make(status_code, body=None, text=None, headers=None):
		response = Mock()
		response.status_code = status_code
		if text is None and body is not None:
			text = json.dumps(body)
		response.text = text or ''
		response.headers = headers or {}
		return response
	return _make


@pytest.fixture
def tmdb_search_response():
	return TMDB_SEARCH_RESPONSE.copy()


@pytest.fixture
def tmdb_episode_response():
	return TMDB_EPISODE_RESPONSE.copy()


@pytest.fixture
def series_list():
	return [
		{'id': 1, 'name': 'The Office', 'year': 2005},
		{'id': 2, 'name': 'The Office', 'year': 2010},
	]


@pytest.fixture
def series_list_without_year():
	return [
		{'id': 1, 'name': 'Mystery Show', 'year': None},
	]


@pytest.fixture
def media_dirs(tmp_path):
	home = tmp_path / 'home'
	moved = tmp_path / 'moved'
	home.mkdir()
	moved.mkdir()
	return home, moved


@pytest.fixture
def config_for_dirs(media_dirs):
	home, moved = media_dirs
	return {
		'MOVIEDB_KEY': 'test-api-key',
		'HOME': str(home),
		'MOVED': str(moved),
	}


@pytest.fixture(autouse=True)
def isolate_rename_history(tmp_path, monkeypatch):
	path = tmp_path / 'rename_history.json'
	monkeypatch.setattr('history.HISTORY_PATH', str(path))
	return path
