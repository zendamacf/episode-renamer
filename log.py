"""
Colored terminal output helpers.
"""

import sys

RESET = '\033[0m'
BOLD = '\033[1m'
CYAN = '\033[36m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'


def _use_color() -> bool:
	return sys.stdout.isatty()


def _print(msg: str, color: str | None = None) -> None:
	if color and _use_color():
		print(f'{color}{msg}{RESET}')
	else:
		print(msg)


def info(msg: str) -> None:
	"""Progress / status messages. Rendered in cyan."""
	_print(msg, CYAN)


def success(msg: str) -> None:
	"""Completed actions. Rendered in green."""
	_print(msg, GREEN)


def warn(msg: str) -> None:
	"""Skips, dry-run, or missing data. Rendered in yellow."""
	_print(msg, YELLOW)


def error(msg: str) -> None:
	"""Parse failures / hard misses. Rendered in red."""
	_print(msg, RED)


def plain(msg: str) -> None:
	"""Uncolored output (e.g. prompt option lists)."""
	_print(msg)


def prompt(msg: str) -> str:
	"""
	Return msg styled for use as an input() prompt. Rendered in bold cyan.
	"""
	if _use_color():
		return f'{BOLD}{CYAN}{msg}{RESET}'
	return msg
