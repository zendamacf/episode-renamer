import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests

import log


class MovieDBException(Exception):
	pass


DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Maximum TMDB search pages loaded per lookup (user-driven or cache validation).
MAX_SEARCH_PAGES = 3


@dataclass
class SeriesSearch:
	query: str
	apikey: str
	page: int = 0
	total_pages: int = 1
	results: list[dict[str, Any]] = field(default_factory=list)
	_seen_ids: set[int] = field(default_factory=set, repr=False)


def _retry_delay(response, attempt: int) -> float:
	retry_after = response.headers.get('Retry-After') if response is not None else None
	if retry_after:
		try:
			return max(float(retry_after), 0.0)
		except ValueError:
			pass
	return float(2**attempt)


def _status_error_message(status_code: int) -> str:
	if status_code in (401, 403):
		return f'TMDB authentication failed ({status_code}). Check your API key.'
	if status_code == 400:
		return f'TMDB rejected the request ({status_code}).'
	if status_code >= 500:
		return f'TMDB server error ({status_code}).'
	return f'TMDB request failed ({status_code}).'


def _request(url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
	"""
	GET from The Movie Database with timeout and bounded retries.
	"""
	headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
	endpoint = f'https://api.themoviedb.org/3{url}'
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
				raise MovieDBException(f'Invalid JSON from TMDB: {exc}') from exc

		if response.status_code == 404:
			return {}

		if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
			time.sleep(_retry_delay(response, attempt))
			continue

		raise MovieDBException(_status_error_message(response.status_code))

	raise MovieDBException(f'TMDB request failed after {MAX_RETRIES} retries: {last_error}')


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


def _parse_search_results(response: dict[str, Any]) -> list[dict[str, Any]]:
	found: list[dict[str, Any]] = []
	for r in response.get('results', []):
		if 'first_air_date' not in r:
			log.warn(r['name'], prefix='Ignoring')
			continue

		country = r.get('origin_country')
		if not country:
			country = None

		found.append(
			{
				'id': r['id'],
				'name': _strip_year(r['name']),
				'year': _extract_year(r['first_air_date']),
				'country': country,
			}
		)
	return found


def search_series_page(query: str, apikey: str, page: int = 1) -> dict[str, Any]:
	"""
	Fetch one page of TMDB ``/search/tv`` results.
	"""
	response = _request(
		'/search/tv',
		params={'api_key': apikey, 'query': query, 'page': str(page)},
	)
	total_pages = int(response.get('total_pages') or 1)
	return {
		'results': _parse_search_results(response),
		'page': page,
		'total_pages': total_pages,
	}


def _load_page(session: SeriesSearch, page: int) -> None:
	data = search_series_page(session.query, session.apikey, page)
	session.page = page
	session.total_pages = data['total_pages']
	for item in data['results']:
		if item['id'] in session._seen_ids:
			continue
		session._seen_ids.add(item['id'])
		session.results.append(item)


def begin_series_search(query: str, apikey: str) -> SeriesSearch:
	"""
	Start a series search with the first TMDB results page.
	"""
	session = SeriesSearch(query=query, apikey=apikey)
	_load_page(session, 1)
	return session


def can_fetch_more(session: SeriesSearch) -> bool:
	return session.page < session.total_pages and session.page < MAX_SEARCH_PAGES


def fetch_next_page(session: SeriesSearch) -> bool:
	"""
	Load the next TMDB page into ``session`` (deduped by id). Returns False when capped or done.
	"""
	if not can_fetch_more(session):
		if session.page < session.total_pages and session.page >= MAX_SEARCH_PAGES:
			log.warn(
				f'top {MAX_SEARCH_PAGES} result pages only (TMDB has {session.total_pages})',
				prefix='TMDB',
			)
		return False
	_load_page(session, session.page + 1)
	if session.page < session.total_pages and session.page >= MAX_SEARCH_PAGES:
		log.warn(
			f'top {MAX_SEARCH_PAGES} result pages only (TMDB has {session.total_pages})',
			prefix='TMDB',
		)
	return True


def find_series_in_search(query: str, apikey: str, series_id: int) -> dict[str, Any] | None:
	"""
	Locate a series id in TMDB search results, loading additional pages up to the cap.
	"""
	session = begin_series_search(query, apikey)
	while True:
		for series in session.results:
			if series['id'] == series_id:
				return series
		if not fetch_next_page(session):
			return None


def get_series(query: str, apikey: str) -> list:
	"""
	Returns the first page of TMDB series matches for a query.
	"""
	return search_series_page(query, apikey, page=1)['results']


def get_episode(seriesid: int, season: int, episode: int, apikey: str) -> str | None:
	"""
	Gets episode information
	"""
	response = _request(
		f'/tv/{seriesid}/season/{season}/episode/{episode}', params={'api_key': apikey}
	)
	if response:
		return response.get('name')
	return None
