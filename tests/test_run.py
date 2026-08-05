from unittest.mock import patch

import moviedb
import run
from helpers import OFFICE, OFFICE_UK


class TestSeriesLabel:
	def test_includes_year_when_present(self):
		assert run._series_label(OFFICE) == 'The Office (2005)'

	def test_omits_year_when_missing(self):
		assert run._series_label({'name': 'Mystery Show', 'year': None}) == (
			'Mystery Show'
		)


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
		assert '[DRY-RUN] No files will be moved' in output
		assert '[DRY-RUN] Skipping rename from The Office S01E01.mp4' in output
		assert 'S01E01 - Pilot.mp4' in output
		assert 'Done: 0 moved, 1 skipped, 0 failed' in output

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_rename_moves_file_to_show_folder(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
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
		output = capsys.readouterr().out
		assert 'Matched The Office (2005) for The Office' in output
		assert f'Successfully moved to {expected}' in output
		assert 'Done: 1 moved, 0 skipped, 0 failed' in output

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_duplicate_destination_logs_and_continues(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		dest_dir = moved / 'The Office (2005)' / 'Season 1'
		dest_dir.mkdir(parents=True)
		(dest_dir / 'S01E01 - Pilot.mp4').write_text('existing')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		output = capsys.readouterr().out
		assert 'Failed processing The Office S01E01.mp4' in output
		assert 'already Exists' in output
		assert 'Done: 0 moved, 0 skipped, 1 failed' in output

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
		assert 'Using previous match The Office (2005) for The Office' in output
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

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_multi_match_prompt_selects_explicit_choice(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, monkeypatch
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE, OFFICE_UK]
		mock_get_episode.return_value = 'Pilot'
		monkeypatch.setattr('builtins.input', lambda _: '2')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		expected = moved / 'The Office (2010)' / 'Season 1' / 'S01E01 - Pilot.mp4'
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

	@patch('run.moviedb.get_series')
	def test_moviedb_error_skips_file(
		self, mock_get_series, media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.side_effect = moviedb.MovieDBException('API error')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		output = capsys.readouterr().out
		assert 'Failed processing The Office S01E01.mp4: API error' in output
		assert 'Done: 0 moved, 0 skipped, 1 failed' in output

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_moviedb_error_continues_with_remaining_files(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		first = 'Bad Show S01E01.mp4'
		second = 'The Office S01E01.mp4'
		(home / first).write_text('video')
		(home / second).write_text('video')
		mock_get_series.side_effect = [
			moviedb.MovieDBException('API error'),
			[OFFICE],
		]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / first).exists()
		expected = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		assert expected.exists()
		assert not (home / second).exists()
		output = capsys.readouterr().out
		assert 'Failed processing Bad Show S01E01.mp4: API error' in output
		assert 'Done: 1 moved, 0 skipped, 1 failed' in output

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_oserror_skips_file_and_continues(
		self, mock_get_series, mock_get_episode,
		media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		first = 'The Office S01E01.mp4'
		second = 'The Office S01E02.mp4'
		(home / first).write_text('video')
		(home / second).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.side_effect = ['Pilot', 'Diversity Day']

		with patch('run.io.read_config', return_value=config_for_dirs):
			with patch(
				'run.io.rename_and_move',
				side_effect=[OSError('disk full'), None],
			):
				run.main(dryrun=False)

		assert (home / first).exists()
		assert (home / second).exists()
		output = capsys.readouterr().out
		assert 'Failed processing The Office S01E01.mp4: disk full' in output
		assert 'Done: 1 moved, 0 skipped, 1 failed' in output
