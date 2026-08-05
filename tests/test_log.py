from unittest.mock import patch

import log
from helpers import assert_logged


class TestLogColors:
	def test_info_plain_when_not_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=False):
			log.info('hello')
		assert capsys.readouterr().out == 'hello\n'

	def test_info_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.info('hello')
		assert capsys.readouterr().out == f'{log.CYAN}hello{log.RESET}\n'

	def test_success_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.success('done')
		assert capsys.readouterr().out == f'{log.GREEN}done{log.RESET}\n'

	def test_warn_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.warn('careful')
		assert capsys.readouterr().out == f'{log.YELLOW}careful{log.RESET}\n'

	def test_error_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.error('fail')
		assert capsys.readouterr().out == f'{log.RED}fail{log.RESET}\n'

	def test_plain_never_colored(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.plain('option')
		assert capsys.readouterr().out == 'option\n'

	def test_prompt_plain_when_not_tty(self):
		with patch('sys.stdout.isatty', return_value=False):
			assert log.prompt('Select: ') == 'Select: '

	def test_promptBOLDCYAN_when_tty(self):
		with patch('sys.stdout.isatty', return_value=True):
			assert log.prompt('Select: ') == (
				f'{log.BOLD}{log.CYAN}Select: {log.RESET}'
			)


class TestLogPrefix:
	def test_prefix_padded_and_uncolored_body_when_not_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=False):
			log.info('file.mkv', prefix='Current')
			log.info('S01E01 - Pilot.mkv', prefix='New')
		out = capsys.readouterr().out
		assert out == (
			f"{'Current:'.ljust(log.PREFIX_WIDTH)}file.mkv\n"
			f"{'New:'.ljust(log.PREFIX_WIDTH)}S01E01 - Pilot.mkv\n"
		)

	def test_prefix_colored_body_plain_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.info('file.mkv', prefix='Current')
		label = 'Current:'.ljust(log.PREFIX_WIDTH)
		assert capsys.readouterr().out == (
			f'{log.BOLD}{log.CYAN}{label}{log.RESET}file.mkv\n'
		)

	def test_success_prefix_uses_green(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.success('/path/out.mkv', prefix='Moved')
		label = 'Moved:'.ljust(log.PREFIX_WIDTH)
		assert capsys.readouterr().out == (
			f'{log.BOLD}{log.GREEN}{label}{log.RESET}/path/out.mkv\n'
		)

	def test_bodies_align_across_prefix_lengths(self, capsys):
		with patch('sys.stdout.isatty', return_value=False):
			log.info('aaa', prefix='Current')
			log.info('bbb', prefix='New')
			log.info('ccc', prefix='Matched')
		lines = capsys.readouterr().out.splitlines()
		assert lines[0].index('aaa') == log.PREFIX_WIDTH
		assert lines[1].index('bbb') == log.PREFIX_WIDTH
		assert lines[2].index('ccc') == log.PREFIX_WIDTH


class TestAssertLogged:
	def test_accepts_prefixed_and_plain_expectations(self):
		output = (
			f"{'Done:'.ljust(log.PREFIX_WIDTH)}1 moved, 0 skipped, 0 failed\n"
			'Running renamer...\n'
		)
		assert_logged(
			output,
			('Done', '1 moved, 0 skipped, 0 failed'),
			'Running renamer...',
		)

	def test_fails_when_prefixed_line_missing(self):
		try:
			assert_logged('other\n', ('Done', '1 moved'))
		except AssertionError as exc:
			assert "Expected 'Done:" in str(exc)
		else:
			raise AssertionError('expected AssertionError')
