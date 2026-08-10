import json

import pytest
from helpers import PARSEABLE_FILENAMES, assert_logged

import file_io as io
import log


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

	def test_missing_key_raises(self, tmp_path):
		path = tmp_path / 'config.json'
		path.write_text(json.dumps({'HOME': '/a', 'MOVED': '/b'}))
		with pytest.raises(io.FileIOException, match='MOVIEDB_KEY'):
			io.read_config(str(path))

	def test_empty_key_raises(self, tmp_path):
		path = tmp_path / 'config.json'
		path.write_text(
			json.dumps(
				{
					'MOVIEDB_KEY': '',
					'HOME': '/a',
					'MOVED': '/b',
				}
			)
		)
		with pytest.raises(io.FileIOException, match='MOVIEDB_KEY'):
			io.read_config(str(path))


class TestIsVideoFile:
	@pytest.mark.parametrize(
		'filename',
		[
			'show.mp4',
			'show.mkv',
			'show.avi',
			'show.flv',
			'show.m4v',
			'show.MP4',
			'show.MkV',
		],
	)
	def test_video_extensions(self, filename):
		assert io.is_video_file(filename) is True

	@pytest.mark.parametrize(
		'filename',
		[
			'show.txt',
			'show.nfo',
			'show.srt',
			'show',
		],
	)
	def test_non_video_extensions(self, filename):
		assert io.is_video_file(filename) is False


class TestIsSubtitleFile:
	@pytest.mark.parametrize(
		'filename',
		[
			'show.srt',
			'show.ass',
			'show.ssa',
			'show.vtt',
			'show.sub',
			'show.SRT',
		],
	)
	def test_subtitle_extensions(self, filename):
		assert io.is_subtitle_file(filename) is True

	@pytest.mark.parametrize(
		'filename',
		[
			'show.mp4',
			'show.txt',
			'show',
		],
	)
	def test_non_subtitle_extensions(self, filename):
		assert io.is_subtitle_file(filename) is False


class TestFindSubtitleCompanions:
	def test_matches_plain_and_lang_tagged_subs(self, tmp_path):
		video = 'The Office S01E01.mp4'
		(tmp_path / video).write_text('video')
		(tmp_path / 'The Office S01E01.srt').write_text('sub')
		(tmp_path / 'The Office S01E01.en.srt').write_text('en')
		(tmp_path / 'The Office S01E01.ass').write_text('ass')
		(tmp_path / 'The Office S01E02.srt').write_text('other')
		(tmp_path / 'readme.txt').write_text('notes')

		found = io.find_subtitle_companions(str(tmp_path), video)

		assert found == [
			{'filename': 'The Office S01E01.ass', 'extension': 'ass'},
			{'filename': 'The Office S01E01.en.srt', 'extension': 'srt'},
			{'filename': 'The Office S01E01.srt', 'extension': 'srt'},
		]

	def test_returns_empty_when_no_companions(self, tmp_path):
		video = 'The Office S01E01.mp4'
		(tmp_path / video).write_text('video')
		assert io.find_subtitle_companions(str(tmp_path), video) == []

	def test_ignores_directories_and_non_subtitle_siblings(self, tmp_path):
		video = 'The Office S01E01.mp4'
		(tmp_path / video).write_text('video')
		(tmp_path / 'The Office S01E01.extras').mkdir()
		(tmp_path / 'The Office S01E01.nfo').write_text('nfo')
		(tmp_path / 'The Office S01E01..srt').write_text('empty-lang')
		(tmp_path / 'The Office S01E01.srt').write_text('sub')

		found = io.find_subtitle_companions(str(tmp_path), video)

		assert found == [{'filename': 'The Office S01E01.srt', 'extension': 'srt'}]


class TestParseFilename:
	@pytest.mark.parametrize(
		'key, expected',
		[
			(
				's01e01',
				{
					'name': 'The Office',
					'season': 1,
					'episode': 1,
					'extension': 'mp4',
				},
			),
			(
				'1x01',
				{
					'name': 'The Office',
					'season': 1,
					'episode': 1,
					'extension': 'mkv',
				},
			),
			(
				'compact',
				{
					'name': 'The Office',
					'season': 1,
					'episode': 2,
					'extension': 'avi',
				},
			),
			(
				'with_year',
				{
					'name': 'The Office 2005',
					'season': 2,
					'episode': 3,
					'extension': 'm4v',
				},
			),
			(
				'encoder_prefix',
				{
					'name': 'Yomi no Tsugai',
					'season': 1,
					'episode': 16,
					'extension': 'mkv',
				},
			),
			(
				'encoder_with_title',
				{
					'name': 'Daemons Of The Shadow Realm',
					'season': 1,
					'episode': 6,
					'extension': 'mkv',
				},
			),
		],
	)
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


class TestGetSubtitleFilename:
	def test_inserts_en_language_tag(self):
		result = io.get_subtitle_filename('orig.srt', 1, 1, 'Pilot', 'srt')
		assert result == 'S01E01 - Pilot.en.srt'

	def test_preserves_subtitle_extension(self):
		result = io.get_subtitle_filename('orig.ass', 2, 3, 'Title', 'ass')
		assert result == 'S02E03 - Title.en.ass'

	def test_strips_unsafe_chars_from_episode_name(self):
		result = io.get_subtitle_filename('orig.srt', 1, 1, 'Pilot: "Start"', 'srt')
		assert result == 'S01E01 - Pilot Start.en.srt'


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
		assert_logged(capsys.readouterr().out, ('Error', 'bad name.mp4'))

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

	def test_prints_name_without_year(self, series_list_without_year, monkeypatch, capsys):
		monkeypatch.setattr('builtins.input', lambda _: '')
		io.prompt_user('Mystery Show', series_list_without_year)
		assert '(1) Mystery Show\n' in capsys.readouterr().out

	def test_passes_styled_prompt_to_input(self, series_list, monkeypatch):
		seen = {}

		def fake_input(prompt):
			seen['prompt'] = prompt
			return ''

		monkeypatch.setattr('builtins.input', fake_input)
		monkeypatch.setattr('sys.stdout.isatty', lambda: True)
		io.prompt_user('The Office', series_list)
		assert seen['prompt'] == (
			f'{log.BOLD}{log.CYAN}Select correct series for The Office ("i" to ignore): {log.RESET}'
		)


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

		io.rename_and_move(str(home), orig, str(moved), new_name, 'The Office', 2005, 1)

		expected = moved / 'The Office (2005)' / 'Season 1' / new_name
		assert expected.exists()
		assert not (home / orig).exists()
		assert_logged(capsys.readouterr().out, ('Moved', str(expected)))

	def test_moves_file_without_year(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', None, 1)

		expected = moved / 'Show' / 'Season 1' / new_name
		assert expected.exists()

	def test_moves_file_when_folders_already_exist(self, dirs, capsys):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')
		season_dir = moved / 'Show (2005)' / 'Season 1'
		season_dir.mkdir(parents=True)

		io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', 2005, 1)

		assert (season_dir / new_name).exists()
		assert not (home / orig).exists()
		assert_logged(
			capsys.readouterr().out,
			('Moved', str(season_dir / new_name)),
		)

	def test_duplicate_destination_raises(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')
		season_dir = moved / 'Show (2005)' / 'Season 1'
		season_dir.mkdir(parents=True)
		(season_dir / new_name).write_text('existing')

		with pytest.raises(io.FileIOException, match='already Exists'):
			io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', 2005, 1)

	def test_sanitizes_unsafe_show_name(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		io.rename_and_move(str(home), orig, str(moved), new_name, 'Evil/Name:Show', 2005, 1)

		expected = moved / 'EvilNameShow (2005)' / 'Season 1' / new_name
		assert expected.exists()
		assert not (moved / 'Evil').exists()
		assert not (home / orig).exists()

	def test_empty_sanitized_show_name_raises(self, dirs):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		with pytest.raises(io.FileIOException, match='empty after sanitization'):
			io.rename_and_move(str(home), orig, str(moved), new_name, '://', 2005, 1)

	def test_cross_device_move_falls_back_to_copy(self, dirs, monkeypatch):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		def fail_replace(src, dst):
			raise OSError('Invalid cross-device link')

		monkeypatch.setattr(io.os, 'replace', fail_replace)

		io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', 2005, 1)

		expected = moved / 'Show (2005)' / 'Season 1' / new_name
		assert expected.exists()
		assert expected.read_text() == 'video'
		assert not (home / orig).exists()

	def test_cross_device_copy_failure_cleans_reserved_dest(self, dirs, monkeypatch):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		def fail_replace(src, dst):
			raise OSError('Invalid cross-device link')

		def fail_copy(src, dst):
			raise OSError('disk full')

		monkeypatch.setattr(io.os, 'replace', fail_replace)
		monkeypatch.setattr(io.shutil, 'copy2', fail_copy)

		with pytest.raises(io.FileIOException, match='Failed to move'):
			io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', 2005, 1)

		expected = moved / 'Show (2005)' / 'Season 1' / new_name
		assert not expected.exists()
		assert (home / orig).exists()

	def test_cross_device_cleanup_ignores_unlink_errors(self, dirs, monkeypatch):
		home, moved = dirs
		orig = 'Show S01E01.mp4'
		new_name = 'S01E01 - Pilot.mp4'
		(home / orig).write_text('video')

		def fail_replace(src, dst):
			raise OSError('Invalid cross-device link')

		def fail_copy(src, dst):
			raise OSError('disk full')

		def fail_unlink(path):
			raise OSError('busy')

		monkeypatch.setattr(io.os, 'replace', fail_replace)
		monkeypatch.setattr(io.shutil, 'copy2', fail_copy)
		monkeypatch.setattr(io.os, 'unlink', fail_unlink)

		with pytest.raises(io.FileIOException, match='Failed to move'):
			io.rename_and_move(str(home), orig, str(moved), new_name, 'Show', 2005, 1)

		assert (home / orig).exists()


class TestRemoveEmptyParents:
	def test_removes_empty_parents_but_stops_at_boundary(self, tmp_path):
		moved = tmp_path / 'moved'
		show = moved / 'The Office (2005)'
		season = show / 'Season 1'
		file_path = season / 'S01E01 - Pilot.mp4'
		season.mkdir(parents=True)

		io.remove_empty_parents(str(file_path), stop_at=str(moved))

		assert not season.exists()
		assert not show.exists()
		assert moved.exists()

	def test_stop_at_survives_even_when_empty(self, tmp_path):
		moved = tmp_path / 'moved'
		moved.mkdir()
		file_path = moved / 'orphan.mp4'

		io.remove_empty_parents(str(file_path), stop_at=str(moved))

		assert moved.exists()
		assert tmp_path.exists()

	def test_stop_at_with_relative_path(self, tmp_path, monkeypatch):
		monkeypatch.chdir(tmp_path)
		moved = tmp_path / 'moved'
		show = moved / 'Show'
		season = show / 'Season 1'
		file_path = season / 'S01E01 - Pilot.mp4'
		season.mkdir(parents=True)

		io.remove_empty_parents(str(file_path), stop_at='moved')

		assert not season.exists()
		assert not show.exists()
		assert moved.exists()

	def test_does_not_remove_non_empty_parent(self, tmp_path):
		moved = tmp_path / 'moved'
		show = moved / 'Show'
		season = show / 'Season 1'
		file_path = season / 'S01E01 - Pilot.mp4'
		season.mkdir(parents=True)
		(season / 'other.mp4').write_text('keep')

		io.remove_empty_parents(str(file_path), stop_at=str(moved))

		assert season.exists()
		assert show.exists()
		assert moved.exists()
		assert (season / 'other.mp4').exists()

	def test_without_stop_at_removes_all_empty_parents(self, tmp_path):
		(tmp_path / 'keep').write_text('anchor')
		root = tmp_path / 'root'
		nested = root / 'a' / 'b' / 'c'
		file_path = nested / 'file.mp4'
		nested.mkdir(parents=True)

		io.remove_empty_parents(str(file_path))

		assert not (root / 'a').exists()
		assert not root.exists()
		assert tmp_path.exists()
		assert (tmp_path / 'keep').exists()
