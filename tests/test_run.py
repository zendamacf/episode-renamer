from unittest.mock import patch

import file_io as io
import history
import moviedb
import run
from helpers import OFFICE, OFFICE_UK, assert_logged


class TestSeriesLabel:
	def test_includes_year_when_present(self):
		assert run._series_label(OFFICE) == 'The Office (2005)'

	def test_omits_year_when_missing(self):
		assert run._series_label({'name': 'Mystery Show', 'year': None}) == ('Mystery Show')


class TestMain:
	def test_no_files_found(self, config_for_dirs, capsys):
		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert_logged(capsys.readouterr().out, ('Skip', 'No files found'))

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
		assert_logged(capsys.readouterr().out, ('No match', 'The Office'))
		mock_get_series.assert_called_once_with('The Office', 'test-api-key')

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_dryrun_does_not_move_file(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=True)

		assert (home / filename).exists()
		assert_logged(
			capsys.readouterr().out,
			('Dry-run', 'No files will be moved'),
			('Dry-run', 'The Office S01E01.mp4 -> S01E01 - Pilot.mp4'),
			('Done', '0 moved, 1 skipped, 0 failed'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_env_moviedb_key_overrides_config(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, monkeypatch, capsys
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'
		monkeypatch.setenv('MOVIEDB_KEY', 'env-api-key')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		mock_get_series.assert_called_once_with('The Office', 'env-api-key')
		mock_get_episode.assert_called_once_with(2316, 1, 1, 'env-api-key')
		expected = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		assert expected.exists()
		assert_logged(
			capsys.readouterr().out,
			('Using', 'MOVIEDB_KEY from environment'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_rename_moves_file_to_show_folder(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
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
		assert_logged(
			capsys.readouterr().out,
			('Matched', 'The Office (2005) for The Office'),
			('Moved', str(expected)),
			('Done', '1 moved, 0 skipped, 0 failed'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_duplicate_destination_logs_and_continues(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		dest_dir = moved / 'The Office (2005)' / 'Season 1'
		dest_dir.mkdir(parents=True)
		dest_file = dest_dir / 'S01E01 - Pilot.mp4'
		dest_file.write_text('existing')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert_logged(
			capsys.readouterr().out,
			('Failed', f'The Office S01E01.mp4: {dest_file} already Exists.'),
			('Done', '0 moved, 0 skipped, 1 failed'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_cached_series_match_calls_get_series_once(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		(home / 'The Office S01E01.mp4').write_text('video')
		(home / 'The Office S01E02.mp4').write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.side_effect = ['Pilot', 'Diversity Day']

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		mock_get_series.assert_called_once()
		assert_logged(
			capsys.readouterr().out,
			('Cached', 'The Office (2005) for The Office'),
		)
		season_dir = moved / 'The Office (2005)' / 'Season 1'
		assert (season_dir / 'S01E01 - Pilot.mp4').exists()
		assert (season_dir / 'S01E02 - Diversity Day.mp4').exists()

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_multi_match_prompt_selects_first(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, monkeypatch
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
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, monkeypatch
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
		self, mock_get_series, media_dirs, config_for_dirs, monkeypatch, capsys
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
		assert_logged(capsys.readouterr().out, ('Ignoring', 'The Office'))

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_episode_not_found_leaves_file(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = None

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert_logged(
			capsys.readouterr().out,
			('No episode', 'The Office S1E1'),
		)

	@patch('run.moviedb.get_series')
	def test_moviedb_error_skips_file(self, mock_get_series, media_dirs, config_for_dirs, capsys):
		home, _ = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.side_effect = moviedb.MovieDBException('API error')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		assert (home / filename).exists()
		assert_logged(
			capsys.readouterr().out,
			('Failed', 'The Office S01E01.mp4: API error'),
			('Done', '0 moved, 0 skipped, 1 failed'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_moviedb_error_continues_with_remaining_files(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
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
		assert_logged(
			capsys.readouterr().out,
			('Failed', 'Bad Show S01E01.mp4: API error'),
			('Done', '1 moved, 0 skipped, 1 failed'),
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_oserror_skips_file_and_continues(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
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
				side_effect=[
					OSError('disk full'),
					str(moved / 'fake' / 'S01E02 - Diversity Day.mp4'),
				],
			):
				run.main(dryrun=False)

		assert (home / first).exists()
		assert (home / second).exists()
		assert_logged(
			capsys.readouterr().out,
			('Failed', 'The Office S01E01.mp4: disk full'),
			('Done', '1 moved, 0 skipped, 1 failed'),
		)


class TestHistoryRecording:
	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_rename_writes_history_batch(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, isolate_rename_history
	):
		home, moved = media_dirs
		filename = 'The Office S01E01.mp4'
		(home / filename).write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		data = history.load_history()
		assert len(data['batches']) == 1
		moves = data['batches'][0]['moves']
		assert len(moves) == 1
		assert moves[0]['src'] == str(home / filename)
		assert moves[0]['dest'] == str(
			moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		)

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_dryrun_does_not_write_history(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, isolate_rename_history
	):
		home, _ = media_dirs
		(home / 'The Office S01E01.mp4').write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=True)

		assert not isolate_rename_history.exists()

	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_multi_file_run_is_one_batch(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs
	):
		home, _ = media_dirs
		(home / 'The Office S01E01.mp4').write_text('video')
		(home / 'The Office S01E02.mp4').write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.side_effect = ['Pilot', 'Diversity Day']

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.main(dryrun=False)

		data = history.load_history()
		assert len(data['batches']) == 1
		assert len(data['batches'][0]['moves']) == 2


class TestUndo:
	def _seed_moved_file(self, home, moved, name='The Office S01E01.mp4'):
		src = home / name
		dest = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		dest.parent.mkdir(parents=True)
		dest.write_text('video')
		history.append_batch([{'src': str(src), 'dest': str(dest)}])
		return src, dest

	def test_undo_restores_file_and_cleans_folders(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		src, dest = self._seed_moved_file(home, moved)

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(1, dryrun=False)

		assert src.exists()
		assert src.read_text() == 'video'
		assert not dest.exists()
		assert not (moved / 'The Office (2005)').exists()
		assert history.load_history()['batches'] == []
		assert_logged(
			capsys.readouterr().out,
			('Undone', '1 restored, 0 failed'),
		)

	def test_undo_dryrun_leaves_files_and_history(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		src, dest = self._seed_moved_file(home, moved)

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(1, dryrun=True)

		assert not src.exists()
		assert dest.exists()
		assert len(history.load_history()['batches']) == 1
		assert_logged(
			capsys.readouterr().out,
			('Dry-run', f'{dest} -> {src}'),
			('Undone', '1 restored, 0 failed'),
		)

	def test_undo_two_batches(self, media_dirs, config_for_dirs):
		home, moved = media_dirs
		src1 = home / 'The Office S01E01.mp4'
		dest1 = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		src2 = home / 'The Office S01E02.mp4'
		dest2 = moved / 'The Office (2005)' / 'Season 1' / 'S01E02 - Diversity Day.mp4'
		dest1.parent.mkdir(parents=True)
		dest1.write_text('one')
		dest2.write_text('two')
		history.append_batch([{'src': str(src1), 'dest': str(dest1)}])
		history.append_batch([{'src': str(src2), 'dest': str(dest2)}])

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(2, dryrun=False)

		assert src1.exists() and src1.read_text() == 'one'
		assert src2.exists() and src2.read_text() == 'two'
		assert history.load_history()['batches'] == []

	def test_undo_missing_dest_retains_failed_move(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		src_ok = home / 'The Office S01E01.mp4'
		dest_ok = moved / 'The Office (2005)' / 'Season 1' / 'S01E01 - Pilot.mp4'
		src_missing = home / 'The Office S01E02.mp4'
		dest_missing = moved / 'The Office (2005)' / 'Season 1' / 'S01E02 - Diversity Day.mp4'
		dest_ok.parent.mkdir(parents=True)
		dest_ok.write_text('ok')
		history.append_batch(
			[
				{'src': str(src_ok), 'dest': str(dest_ok)},
				{'src': str(src_missing), 'dest': str(dest_missing)},
			]
		)

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(1, dryrun=False)

		assert src_ok.exists()
		data = history.load_history()
		assert len(data['batches']) == 1
		assert data['batches'][0]['moves'] == [
			{'src': str(src_missing), 'dest': str(dest_missing)},
		]
		assert_logged(
			capsys.readouterr().out,
			('Undone', '1 restored, 1 failed'),
		)

	def test_undo_collision_retains_failed_move(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		src, dest = self._seed_moved_file(home, moved)
		src.write_text('occupying')

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(1, dryrun=False)

		assert dest.exists()
		assert src.read_text() == 'occupying'
		data = history.load_history()
		assert len(data['batches']) == 1
		assert data['batches'][0]['moves'][0]['dest'] == str(dest)
		assert_logged(
			capsys.readouterr().out,
			('Cannot', f'original path occupied: {src}'),
		)

	def test_undo_with_no_history(self, config_for_dirs, capsys):
		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(1, dryrun=False)

		assert_logged(
			capsys.readouterr().out,
			('Skip', 'No rename history to undo'),
		)

	def test_undo_rejects_non_positive_count(self, config_for_dirs, capsys):
		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(0, dryrun=False)

		assert_logged(
			capsys.readouterr().out,
			('Error', 'Undo count must be at least 1'),
		)

	def test_undo_load_history_error(self, config_for_dirs, capsys):
		with patch('run.io.read_config', return_value=config_for_dirs):
			with patch(
				'run.history.load_history',
				side_effect=history.HistoryException('corrupt'),
			):
				run.undo_batches(1, dryrun=False)

		assert_logged(capsys.readouterr().out, ('Error', 'corrupt'))

	def test_undo_warns_when_requesting_more_batches_than_available(
		self, media_dirs, config_for_dirs, capsys
	):
		home, moved = media_dirs
		self._seed_moved_file(home, moved)

		with patch('run.io.read_config', return_value=config_for_dirs):
			run.undo_batches(5, dryrun=False)

		assert_logged(
			capsys.readouterr().out,
			('Warn', 'Requested 5 batch(es) but only 1 available'),
			('Undone', '1 restored, 0 failed'),
		)

	def test_undo_save_history_error(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		self._seed_moved_file(home, moved)

		with patch('run.io.read_config', return_value=config_for_dirs):
			with patch(
				'run.history.save_history',
				side_effect=history.HistoryException('write failed'),
			):
				run.undo_batches(1, dryrun=False)

		assert_logged(capsys.readouterr().out, ('Error', 'write failed'))

	def test_undo_move_file_failure_is_reported(self, media_dirs, config_for_dirs, capsys):
		home, moved = media_dirs
		src, dest = self._seed_moved_file(home, moved)

		with patch('run.io.read_config', return_value=config_for_dirs):
			with patch(
				'run.io.move_file',
				side_effect=io.FileIOException('cross-device failed'),
			):
				run.undo_batches(1, dryrun=False)

		assert dest.exists()
		assert not src.exists()
		assert_logged(
			capsys.readouterr().out,
			('Failed', f'{dest} -> {src}: cross-device failed'),
			('Undone', '0 restored, 1 failed'),
		)
		assert len(history.load_history()['batches']) == 1


class TestHistoryRecordingErrors:
	@patch('run.moviedb.get_episode')
	@patch('run.moviedb.get_series')
	def test_append_batch_failure_is_logged(
		self, mock_get_series, mock_get_episode, media_dirs, config_for_dirs, capsys
	):
		home, _ = media_dirs
		(home / 'The Office S01E01.mp4').write_text('video')
		mock_get_series.return_value = [OFFICE]
		mock_get_episode.return_value = 'Pilot'

		with patch('run.io.read_config', return_value=config_for_dirs):
			with patch(
				'run.history.append_batch',
				side_effect=history.HistoryException('cannot write'),
			):
				run.main(dryrun=False)

		assert_logged(
			capsys.readouterr().out,
			('History', 'cannot write'),
			('Done', '1 moved, 0 skipped, 0 failed'),
		)
