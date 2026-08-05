from unittest.mock import patch

import log


class TestLogColors:
	def test_info_plain_when_not_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=False):
			log.info('hello')
		assert capsys.readouterr().out == 'hello\n'

	def test_info_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.info('hello')
		assert capsys.readouterr().out == '\033[36mhello\033[0m\n'

	def test_success_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.success('done')
		assert capsys.readouterr().out == '\033[32mdone\033[0m\n'

	def test_warn_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.warn('careful')
		assert capsys.readouterr().out == '\033[33mcareful\033[0m\n'

	def test_error_colored_when_tty(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.error('fail')
		assert capsys.readouterr().out == '\033[31mfail\033[0m\n'

	def test_plain_never_colored(self, capsys):
		with patch('sys.stdout.isatty', return_value=True):
			log.plain('option')
		assert capsys.readouterr().out == 'option\n'
