import requests
import json
import re
import time
from datetime import datetime
from typing import Any

import log


class MovieDBException(Exception):
	pass


DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _retry_delay(response, attempt: int) -> float:
	retry_after = response.headers.get('Retry-After') if response is not None else None
	if retry_after:
		try:
			return max(float(retry_after), 0.0)
		except ValueError:
			pass
	return float(2**attempt)


def _request(url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
	"""
	GET from The Movie Database with timeout and bounded retries.
	"""
	headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	endpoint = 'https://api.themoviedb.org/3{}'.format(url)
	last_error = None

	for attempt in range(MAX_RETRIES):
		response = None
		try:
			response = requests.get(
				endpoint,
				params=params,
				headers=headers,
				timeout=DEFAULT_TIMEOUT,
			)
		except requests.RequestException as exc:
			last_error = exc
			time.sleep(_retry_delay(None, attempt))
			continue

		if response.status_code == 200:
			try:
				return json.loads(response.text)
			except json.JSONDecodeError as exc:
				raise MovieDBException('Invalid JSON from TMDB: {}'.format(exc)) from exc

		if response.status_code == 404:
			return {}

		if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
			time.sleep(_retry_delay(response, attempt))
			continue

		raise MovieDBException(
			'Unexpected response ({}): {}'.format(response.status_code, response.text)
		)

	raise MovieDBException(
		'TMDB request failed after {} retries: {}'.format(MAX_RETRIES, last_error)
	)


def _strip_year(nam: str) -> str:
	"""
	Removes year from show title
	"""
	return re.sub(r'\([0-9]{4}\)', '', nam).strip()


def _extract_year(dat: str | None) -> int | None:
	"""
	Extracts year from an ISO date string
	"""
	if not dat:
		return None
	try:
		return datetime.strptime(dat, '%Y-%m-%d').year
	except ValueError:
		return None


def get_series(query: str, apikey: str) -> list:
	"""
	Returns list of series in The Movie DB matching given query
	"""
	params = {'api_key': apikey, 'query': query}
	response = _request('/search/tv', params=params)

	found = []
	for r in response.get('results', []):
		if 'first_air_date' not in r:
			log.warn(r['name'], prefix='Ignoring')
			continue

		found.append(
			{
				'id': r['id'],
				'name': _strip_year(r['name']),
				'year': _extract_year(r['first_air_date']),
			}
		)
	return found


def get_episode(seriesid: int, season: int, episode: int, apikey: str) -> str | None:
	"""
	Gets episode information
	"""
	response = _request(
		'/tv/{}/season/{}/episode/{}'.format(seriesid, season, episode), params={'api_key': apikey}
	)
	if response:
		return response.get('name')
