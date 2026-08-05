import log

PARSEABLE_FILENAMES = {
	's01e01': 'The Office S01E01.mp4',
	'1x01': 'The Office 1x01.mkv',
	'compact': 'The Office 102.avi',
	'with_year': 'The Office 2005 S02E03.m4v',
}

TMDB_SEARCH_RESPONSE = {
	'results': [
		{'id': 2316, 'name': 'The Office', 'first_air_date': '2005-03-24'},
		{'id': 9999, 'name': 'The Office (2010)', 'first_air_date': '2010-01-01'},
		{'id': 8888, 'name': 'No Date Show'},
	],
}

TMDB_EPISODE_RESPONSE = {'name': 'Pilot'}

OFFICE = {'id': 2316, 'name': 'The Office', 'year': 2005}
OFFICE_UK = {'id': 9999, 'name': 'The Office', 'year': 2010}


def assert_logged(output: str, *expectations: tuple[str, str] | str) -> None:
	"""
	Assert logged output contains the given entries.

	Pass ``(prefix, message)`` for a padded prefix line matching
	``log.PREFIX_WIDTH``, or a plain string for a substring match.
	"""
	for item in expectations:
		if isinstance(item, str):
			needle = item
		else:
			prefix, message = item
			needle = f'{prefix}:'.ljust(log.PREFIX_WIDTH) + message
		assert needle in output, (
			f'Expected {needle!r} in logged output:\n{output}'
		)
