import json

import pytest

import file_io as io
from helpers import PARSEABLE_FILENAMES


class TestReadConfig:
	def test_reads_json_config(self, config_file, sample_config):
		assert io.read_config(str(config_file)) == sample_config

	def test_missing_file_raises(self, tmp_path):
		with pytest.raises(FileNotFoundError):
			io.read_config(str(tmp_path / 'missing.json'))

	def test_invalid_json_raises(self, tmp_path):
		path = tmp_path / 'bad.json'
		path.write_text('{not json')
		with pytest.raises(json.JSONDecodeError):
			io.read_config(str(path))


class TestIsVideoFile:
	@pytest.mark.parametrize('filename', [
		'show.mp4', 'show.mkv', 'show.avi', 'show.flv', 'show.m4v',
	])
	def test_video_extensions(self, filename):
		assert io.is_video_file(filename) is True

	@pytest.mark.parametrize('filename', [
		'show.txt', 'show.nfo', 'show.srt', 'show',
	])
	def test_non_video_extensions(self, filename):
		assert io.is_video_file(filename) is False


class TestParseFilename:
	@pytest.mark.parametrize('key, expected', [
		('s01e01', {
			'name': 'The Office', 'season': 1, 'episode': 1, 'extension': 'mp4',
		}),
		('1x01', {
			'name': 'The Office', 'season': 1, 'episode': 1, 'extension': 'mkv',
		}),
		('compact', {
			'name': 'The Office', 'season': 1, 'episode': 2, 'extension': 'avi',
		}),
		('with_year', {
			'name': 'The Office 2005', 'season': 2, 'episode': 3,
			'extension': 'm4v',
		}),
	])
	def test_parse_formats(self, key, expected):
		filename = PARSEABLE_FILENAMES[key]
		result = io.parse_filename(filename)
		assert result['name'] == expected['name']
		assert result['season'] == expected['season']
		assert result['episode'] == expected['episode']
		assert result['extension'] == expected['extension']
		assert result['filename'] == filename

	def test_dots_in_name_become_spaces(self):
		result = io.parse_filename('The.Office.S01E01.mp4')
		assert result['name'] == 'The Office'

	def test_unmatched_filename_raises(self):
		with pytest.raises(io.FileIOException, match='Filename not matched'):
			io.parse_filename('not_a_valid_filename.mp4')


class TestWinsafeFilename:
	def test_strips_unsafe_characters(self):
		unsafe = 'S01E01 - Episode: "Title"?.mp4'
		assert io.winsafe_filename(unsafe) == 'S01E01 - Episode Title.mp4'


class TestGetFilename:
	def test_zero_pads_season_and_episode(self):
		result = io.get_filename('orig.mp4', 1, 2, 'Pilot', 'mp4')
		assert result == 'S01E02 - Pilot.mp4'

	def test_no_padding_for_double_digits(self):
		result = io.get_filename('orig.mp4', 10, 12, 'Finale', 'mkv')
		assert result == 'S10E12 - Finale.mkv'

	def test_strips_unsafe_chars_from_episode_name(self):
		result = io.get_filename('orig.mp4', 1, 1, 'Pilot: "Start"', 'mp4')
		assert result == 'S01E01 - Pilot Start.mp4'


class TestFindFiles:
	def test_finds_parseable_video_files(self, tmp_path):
		for filename in PARSEABLE_FILENAMES.values():
			(tmp_path / filename).write_text('video')
		(tmp_path / 'readme.txt').write_text('notes')

		found = io.find_files(str(tmp_path))

		assert len(found) == len(PARSEABLE_FILENAMES)
		names = {f['filename'] for f in found}
		assert names == set(PARSEABLE_FILENAMES.values())

	def test_skips_unparseable_video_files(self, tmp_path, capsys):
		(tmp_path / 'bad name.mp4').write_text('video')
		(tmp_path / PARSEABLE_FILENAMES['s01e01']).write_text('video')

		found = io.find_files(str(tmp_path))

		assert len(found) == 1
		assert found[0]['filename'] == PARSEABLE_FILENAMES['s01e01']
		assert 'Error parsing bad name.mp4' in capsys.readouterr().out

	def test_ignores_non_video_files(self, tmp_path):
		(tmp_path / 'notes.txt').write_text('notes')
		(tmp_path / PARSEABLE_FILENAMES['s01e01']).write_text('video')

		found = io.find_files(str(tmp_path))

		assert len(found) == 1


class TestPromptUser:
	def test_empty_input_selects_first(self, series_list, monkeypatch):
		monkeypatch.setattr('builtins.input', lambda _: '')
		chosen = io.prompt_user('The Office', series_list)
		assert chosen == series_list[0]

	def test_ignore_returns_none(self, series_list, monkeypatch):
		monkeypatch.setattr('builtins.input', lambda _: 'i')
		assert io.prompt_user('The Office', series_list) is None

	def test_valid_choice_selects_entry(self, series_list, monkeypatch):
		monkeypatch.setattr('builtins.input', lambda _: '2')
		chosen = io.prompt_user('The Office', series_list)
		assert chosen == series_list[1]

	def test_invalid_choice_raises(self, series_list, monkeypatch):
		monkeypatch.setattr('builtins.input', lambda _: '99')
		with pytest.raises(io.FileIOException, match='Invalid input'):
			io.prompt_user('The Office', series_list)

	def test_non_numeric_input_raises(self, series_list, monkeypatch):
		monkeypatch.setattr('builtins.input', lambda _: 'abc')
		with pytest.raises(io.FileIOException, match='Invalid input'):
			io.prompt_user('The Office', series_list)

	def test_prints_name_without_year(
		self, series_list_without_year, monkeypatch, capsys
	):
		monkeypatch.setattr('builtins.input', lambda _: '')
		io.prompt_user('Mystery Show', series_list_without_year)
		assert '(1) Mystery Show\n' in capsys.readouterr().out


class TestRenameAndMove:
	@pytest.fixture
	def dirs(self, tmp_path):
		home = tmp_path / 'home'
		moved = tmp_path / 'moved'
		home.mkdir()
		moved.mkdir()
		return home, moved

	def test_moves_file_with_year(self, dirs, capsys):
		home, moved = dirs
		orig = 'The Office S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		io.rename_and_move(
			str(home), orig, str(moved), new_name,
			'The Office', 2005, 1
		)

		expected = moved / 'The Office (2005)' / 'Season 1' / new_name
		assert expected.exists()
		assert not (home / orig).exists()
		output = capsys.readouterr().out
		assert f'Created show folder: {moved / "The Office (2005)"}' in output
		assert f'Created season folder: {expected.parent}' in output
		assert f'Successfully moved to {expected}' in output

	def test_moves_file_without_year(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		io.rename_and_move(
			str(home), orig, str(moved), new_name,
			'Show', None, 1
		)

		expected = moved / 'Show' / 'Season 1' / new_name
		assert expected.exists()

	def test_moves_file_when_folders_already_exist(self, dirs, capsys):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')
		season_dir = moved / 'Show (2005)' / 'Season 1'
		season_dir.mkdir(parents=True)

		io.rename_and_move(
			str(home), orig, str(moved), new_name,
			'Show', 2005, 1
		)

		assert (season_dir / new_name).exists()
		assert not (home / orig).exists()
		output = capsys.readouterr().out
		assert 'Created show folder' not in output
		assert 'Created season folder' not in output
		assert f'Successfully moved to {season_dir / new_name}' in output

	def test_duplicate_destination_raises(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')
		season_dir = moved / 'Show (2005)' / 'Season 1'
		season_dir.mkdir(parents=True)
		(season_dir / new_name).write_text('existing')

		with pytest.raises(io.FileIOException, match='already Exists'):
			io.rename_and_move(
				str(home), orig, str(moved), new_name,
				'Show', 2005, 1
			)
