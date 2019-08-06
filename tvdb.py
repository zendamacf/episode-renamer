import json
import requests
import re
from datetime import datetime


class TVDBException(Exception):
	pass


def _request(
	url: str,
	method: str,
	params: dict = None,
	data: str = None,
	token: str = None
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
	if token:
		headers['Authorization'] = 'Bearer {}'.format(token)

	response = func(
		'https://api.thetvdb.com{}'.format(url),
		params=params,
		data=data,
		headers=headers
	)
	if response.status_code == 503:
		raise TVDBException('TVDB currently down. Please try again later.')

	resp = json.loads(response.text)
	if 'Error' in resp and response.status_code != 404:  # Returns 404 if no search results found
		raise TVDBException(resp['Error'])

	return resp


def login(apikey: str, userkey: str, username: str) -> str:
	"""
	Makes login request to tvdb, required for their REST API
	"""
	data = {
		'apikey': apikey,
		'userkey': userkey,
		'username': username
	}
	response = _request(
		'/login',
		'POST',
		data=json.dumps(data)
	)
	return response['token']


def strip_year(nam: str) -> str:
	"""
	Removes year from show title
	"""
	return re.sub(r"\([0-9]{4}\)", '', nam).strip()


def extract_year(dat: str) -> str:
	"""
	Extracts year from an ISO date string
	"""
	if not dat:
		return None
	return datetime.strptime(dat, "%Y-%m-%d").year


def get_series(name: str, token: str) -> list:
	"""
	Returns list of series in TVDB matching given name
	"""
	params = {'name': name}
	response = _request(
		'/search/series',
		'GET',
		params=params,
		token=token
	)

	found = []
	for r in response['data']:
		found.append({
			'id': r['id'],
			'name': strip_year(r['seriesName']),
			'year': extract_year(r['firstAired'])
		})
	return found


def get_episode(seriesid: int, season: int, episode: int, token: str) -> str:
	"""
	Gets episode information
	"""
	params = {'airedSeason': season, 'airedEpisode': episode}
	response = _request(
		'/series/{}/episodes/query'.format(seriesid),
		'GET',
		params=params,
		token=token
	)

	episode_name = None
	for r in response.get('data', []):  # Using .get in case of no results found 
		if int(r['airedSeason']) == int(season) and int(r['airedEpisodeNumber']) == int(episode):
			episode_name = r['episodeName']

	return episode_name
