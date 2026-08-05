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

# Width of the "Prefix:" column so message bodies vertically align.
PREFIX_WIDTH = 12


def _use_color() -> bool:
	return sys.stdout.isatty()


def _format_line(msg: str, color: str | None, prefix: str | None) -> str:
	if prefix is None:
		if color and _use_color():
			return f'{color}{msg}{RESET}'
		return msg

	label = f'{prefix}:'.ljust(PREFIX_WIDTH)
	if color and _use_color():
		return f'{BOLD}{color}{label}{RESET}{msg}'
	return f'{label}{msg}'


def _print(msg: str, color: str | None = None, prefix: str | None = None) -> None:
	print(_format_line(msg, color, prefix))


def info(msg: str, *, prefix: str | None = None) -> None:
	"""Progress / status messages. Prefix rendered in bold cyan."""
	_print(msg, CYAN, prefix)


def success(msg: str, *, prefix: str | None = None) -> None:
	"""Completed actions. Prefix rendered in bold green."""
	_print(msg, GREEN, prefix)


def warn(msg: str, *, prefix: str | None = None) -> None:
	"""Skips, dry-run, or missing data. Prefix rendered in bold yellow."""
	_print(msg, YELLOW, prefix)


def error(msg: str, *, prefix: str | None = None) -> None:
	"""Parse failures / hard misses. Prefix rendered in bold red."""
	_print(msg, RED, prefix)


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
