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
