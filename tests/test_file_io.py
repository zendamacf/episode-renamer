import pytest

import file_io as io

PARSEABLE_FILENAMES = {
	's01e01': 'The Office S01E01.mp4',
	'1x01': 'The Office 1x01.mkv',
	'compact': 'The Office 102.avi',
	'with_year': 'The Office 2005 S02E03.m4v',
}


class TestReadConfig:
	def test_reads_json_config(self, config_file, sample_config):
		assert io.read_config(str(config_file)) == sample_config


class TestIsVideoFile:
	@pytest.mark.parametrize('filename', [
		'show.mp4', 'show.mkv', 'show.avi', 'show.flv', 'show.m4v',
	])
	def test_video_extensions(self, filename):
		assert io.is_video_file(filename) is True

	@pytest.mark.parametrize('filename', [
		'show.txt', 'show.nfo', 'show.srt',
	])
	def test_non_video_extensions(self, filename):
		assert io.is_video_file(filename) is False


class TestParseFilename:
	def test_s01e01_format(self):
		result = io.parse_filename(PARSEABLE_FILENAMES['s01e01'])
		assert result['name'] == 'The Office'
		assert result['season'] == 1
		assert result['episode'] == 1
		assert result['extension'] == 'mp4'
		assert result['filename'] == PARSEABLE_FILENAMES['s01e01']

	def test_1x01_format(self):
		result = io.parse_filename(PARSEABLE_FILENAMES['1x01'])
		assert result['name'] == 'The Office'
		assert result['season'] == 1
		assert result['episode'] == 1
		assert result['extension'] == 'mkv'

	def test_compact_format(self):
		result = io.parse_filename(PARSEABLE_FILENAMES['compact'])
		assert result['name'] == 'The Office'
		assert result['season'] == 1
		assert result['episode'] == 2
		assert result['extension'] == 'avi'

	def test_with_year_in_name(self):
		result = io.parse_filename(PARSEABLE_FILENAMES['with_year'])
		assert result['name'] == 'The Office 2005'
		assert result['season'] == 2
		assert result['episode'] == 3
		assert result['extension'] == 'm4v'

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


class TestRenameAndMove:
	def test_moves_file_with_year(self, tmp_path):
		home = tmp_path / 'home'
		moved = tmp_path / 'moved'
		home.mkdir()
		moved.mkdir()
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

	def test_moves_file_without_year(self, tmp_path):
		home = tmp_path / 'home'
		moved = tmp_path / 'moved'
		home.mkdir()
		moved.mkdir()
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		io.rename_and_move(
			str(home), orig, str(moved), new_name,
			'Show', None, 1
		)

		expected = moved / 'Show' / 'Season 1' / new_name
		assert expected.exists()

	def test_duplicate_destination_raises(self, tmp_path):
		home = tmp_path / 'home'
		moved = tmp_path / 'moved'
		home.mkdir()
		moved.mkdir()
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')
		dest_dir = moved / 'Show (2005)' / 'Season 1'
		dest_dir.mkdir(parents=True)
		(dest_dir / new_name).write_text('existing')

		with pytest.raises(io.FileIOException, match='already Exists'):
			io.rename_and_move(
				str(home), orig, str(moved), new_name,
				'Show', 2005, 1
			)
