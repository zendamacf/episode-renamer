import json

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
def series_list():
	return [
		{'id': 1, 'name': 'The Office', 'year': 2005},
		{'id': 2, 'name': 'The Office', 'year': 2010},
	]
