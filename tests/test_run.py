from unittest.mock import patch

import pytest

import run

OFFICE = {'id': 2316, 'name': 'The Office', 'year': 2005}
OFFICE_UK = {'id': 9999, 'name': 'The Office', 'year': 2010}


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


class TestMain:
	def test_no_files_found(self, config_for_dirs, capsys):
		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert 'No files found' in capsys.readouterr().out

	@patch('run.moviedb.get_series')
	def test_no_series_match_leaves_file(
		self, mock_get_series, media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = []

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert 'No series matches for The Office' in capsys.readouterr().out
		mock_get_series.assert_called_once_with('The Office', 'test-api-key')

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_dryrun_does_not_move_file(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=True)

		output = capsys.readouterr().out
		assert (home / filename).exists()
		assert '[DRYRUN] Skipping rename from The Office S01E01.mp4' in output
		assert 'S01E01 - Pilot.mp4' in output

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_rename_moves_file_to_show_folder(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		expected = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		assert expected.exists()
		assert not (home / filename).exists()

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_cached_series_match_calls_get_series_once(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		(home / 'The Office S01E01.mp4').write_text('video')
		(home / 'The Office S01E02.mp4').write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.side_effect = ['Pilot', 'Diversity Day']

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		mock_get_series.assert_called_once()
		output = capsys.readouterr().out
		assert 'Using previous match The Office for The Office' in output
		season_dir = moved / 'The Office (2005)' / 'Season 1'
		assert (season_dir / 'S01E01 - Pilot.mp4').exists()
		assert (season_dir / 'S01E02 - Diversity Day.mp4').exists()

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_multi_match_prompt_selects_first(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, monkeypatch
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE, OFFICE_UK]
		mock_get_episode.return_value = 'Pilot'
		monkeypatch.setattr('builtins.input', lambda _: '')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		expected = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		assert expected.exists()

	@patch('run.moviedb.get_series')
	def test_multi_match_prompt_ignore_skips_file(
		self, mock_get_series, media_dirs, config_for_dirs,
		monkeypatch, capsys
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE, OFFICE_UK]
		monkeypatch.setattr('builtins.input', lambda _: 'i')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert not list(moved.iterdir())
		assert 'Ignoring The Office' in capsys.readouterr().out

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_episode_not_found_leaves_file(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = None

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert 'No episode found for The Office S1E1' in capsys.readouterr().out
