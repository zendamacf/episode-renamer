"""
Colored terminal output helpers.
"""

import sys

_RESET = '\033[0m'
_CYAN = '\033[36m'
_GREEN = '\033[32m'
_YELLOW = '\033[33m'
_RED = '\033[31m'


def _use_color() -> bool:
	return sys.stdout.isatty()


def _print(msg: str, color: str | None = None) -> None:
	if color and _use_color():
		print(f'{color}{msg}{_RESET}')
	else:
		print(msg)


def info(msg: str) -> None:
	"""Progress / status messages."""
	_print(msg, _CYAN)


def success(msg: str) -> None:
	"""Completed actions."""
	_print(msg, _GREEN)


def warn(msg: str) -> None:
	"""Skips, dry-run, or missing data."""
	_print(msg, _YELLOW)


def error(msg: str) -> None:
	"""Parse failures / hard misses."""
	_print(msg, _RED)


def plain(msg: str) -> None:
	"""Uncolored output (e.g. prompt option lists)."""
	_print(msg)
