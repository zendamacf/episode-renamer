import requests
import json
import re
from datetime import datetime


class MovieDBException(Exception):
	pass


def _request(
	url: str,
	method: str,
	params: dict = None,
	data: str = None
) -> dict:
	"""
	Sends a request to the TVDB REST API
	"""
	if method.upper() == 'POST':
		func = requests.post
	else:
		func = requests.get

	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	response = func(
		'https://api.themoviedb.org/3{}'.format(url),
		params=params,
		data=data,
		headers=headers
	)

	resp = {}
	if response.status_code == 200:
		resp = json.loads(response.text)
	elif response.status_code != 404:
		raise MovieDBException('Unexpected response: {}'.format(response.text))

	return resp


def _strip_year(nam: str) -> str:
	"""
	Removes year from show title
	"""
	return re.sub(r"\([0-9]{4}\)", '', nam).strip()


def _extract_year(dat: str) -> str:
	"""
	Extracts year from an ISO date string
	"""
	if not dat:
		return None
	return datetime.strptime(dat, "%Y-%m-%d").year


def get_series(query: str, apikey: str) -> list:
	"""
	Returns list of series in The Movie DB matching given query
	"""
	params = {'api_key': apikey, 'query': query}
	response = _request(
		'/search/tv',
		'GET',
		params=params
	)

	found = []
	for r in response['results']:
		found.append({
			'id': r['id'],
			'name': _strip_year(r['name']),
			'year': _extract_year(r['first_air_date'])
		})
	return found


def get_episode(seriesid: int, season: int, episode: int, apikey: str) -> str:
	"""
	Gets episode information
	"""
	response = _request(
		'/tv/{}/season/{}/episode/{}'.format(seriesid, season, episode),
		'GET',
		params={'api_key': apikey}
	)
	if response:
		return response['name']
