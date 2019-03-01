"""
Searches for tv show episode files, and renames & sorts, them
using information from thetvdb
"""

import re
import os
import shutil
import json
import requests

CONFIG = {}


class RenamrException(Exception):
	pass


def parse_filename(filename):
	"""
	Uses regex to pull series name, season and episode numbers
	"""
	regex_parsers = [
		r"^(?P<show>.*?)s *(?P<season>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$",
		r"^(?P<show>.*?)(?P<season>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$",
		r"^(?P<show>(?:.*?\D|))(?P<season>\d{1,2})(?P<episode>\d{2})(?:\D.*|)\.(?P<extension>.*?)$",
	]
	for parser in regex_parsers:
		matches = re.compile(parser, re.IGNORECASE).search(filename)
		try:
			match_dict = matches.groupdict()
			break
		except AttributeError:
			continue
	else:
		raise RenamrException('Filename not matched.')

	show = match_dict['show'].replace('.', ' ').strip()
	season = str(int(match_dict['season']))
	episode = str(int(match_dict['episode']))
	extension = match_dict['extension']

	seriesid, show = get_seriesid(show)
	if seriesid is None or show is None:
		raise RenamrException('Ignoring file.')
	episodename = get_episode(seriesid, season, episode)
	if episodename is None:
		raise RenamrException('Couldn\'t find %s S%sE%s.' % (show, season, episode,))

	rename = check_with_user(filename, season, episode, episodename, extension)
	if rename:
		rename_and_move(filename, rename, show, season)


def get_headers():
	"""
	Gets headers needed for tvdb request
	"""
	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json',
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
	}
	return headers


def login():
	"""
	Makes login request to tvdb, required for their REST API
	"""
	data = {
		'apikey': CONFIG['TVDB_KEY'],
		'userkey': CONFIG['TVDB_USER'],
		'username': CONFIG['TVDB_NAME']
	}
	headers = get_headers()
	response = requests.post('https://api.thetvdb.com/login', data=json.dumps(data), headers=headers)
	if response.status_code == 503:
		raise RenamrException('TVDB currently down. Please try again later.')
	resp = response.text
	resp = json.loads(resp)
	if 'Error' in resp:
		raise RenamrException(resp['Error'])
	return resp['token']


def get_seriesid(show):
	"""
	Finds series in tvdb
	Will prompt user to select series if multiple found
	"""
	params = {'name': show}
	headers = get_headers()
	headers['Authorization'] = 'Bearer %s' % CONFIG['TVDB_TOKEN']
	resp = requests.get('https://api.thetvdb.com/search/series', params=params, headers=headers).text
	resp = json.loads(resp)

	if 'Error' in resp:
		raise RenamrException(resp['Error'])

	found = resp['data']

	if not found:
		raise RenamrException('No series matches for %s' % (show,))
	elif len(found) == 1:
		return found[0]['id'], found[0]['seriesName']
	else:
		for count, value in enumerate(found):
			print('(%s) %s' % (count + 1, value['seriesName']))
		choice = input('Select correct series for %s ("i" to ignore): ' % (show,))
		if choice == '':
			return found[0]['id'], found[0]['seriesName']
		elif choice == 'i':
			return None, None
		elif int(choice) < 1 or int(choice) > len(found):
			raise RenamrException('Invalid input.')
		else:
			return found[int(choice) - 1]['id'], found[int(choice) - 1]['seriesName']


def get_episode(seriesid, season, episode):
	"""
	Gets episode information
	"""
	params = {'airedSeason': season, 'airedEpisode': episode}
	headers = get_headers()
	headers['Authorization'] = 'Bearer %s' % CONFIG['TVDB_TOKEN']
	url = 'https://api.thetvdb.com/series/%s/episodes/query' % seriesid
	resp = requests.get(url, params=params, headers=headers).text
	resp = json.loads(resp)

	if 'Error' in resp:
		raise RenamrException(resp['Error'])

	found = resp['data']

	episode_name = None

	for epi in found:
		if int(epi['airedSeason']) == int(season) and int(epi['airedEpisodeNumber']) == int(episode):
			episode_name = epi['episodeName']

	return episode_name


def check_with_user(filename, season, episode, episodename, extension):
	"""
	Notify user of filename change
	"""
	if int(season) < 10:
		season = '0' + season
	if int(episode) < 10:
		episode = '0' + episode
	new_filename = 'S%sE%s - %s.%s' % (season, episode, episodename, extension)
	print('Current: %s' % (filename,))
	print('New: %s' % (new_filename,))
	return winsafe_filename(new_filename)


def rename_and_move(filename, new_filename, show, season):
	"""
	Rename and sort the file into folders
	"""
	show_folder = os.path.join(CONFIG['MOVED'], show)
	if not os.path.exists(show_folder):
		os.makedirs(show_folder)
	season_folder = os.path.join(show_folder, 'Season %s' % (season,))
	if not os.path.exists(season_folder):
		os.makedirs(season_folder)
	curr_file = os.path.join(CONFIG['HOME'], filename)
	new_file = os.path.join(season_folder, new_filename)
	if os.path.exists(new_file):
		raise RenamrException('%s already Exists.' % (new_file,))
	shutil.move(curr_file, new_file)
	print('Successfully moved.')


def winsafe_filename(filename):
	"""
	Make a windows-safe filename
	"""
	return re.sub(r'[\\/:"*?<>|]+', "", filename)


def main():
	"""
	Main function
	"""
	print('Running renamr...')
	with open('config.cfg') as file:
		content = file.readlines()
	for line in content:
		(key, value) = line.replace('\n', '').split(' = ')
		CONFIG[key] = value

	CONFIG['TVDB_TOKEN'] = login()

	print('Checking for files in %s' % CONFIG['HOME'])
	for file in os.listdir(CONFIG['HOME']):
		if os.path.isfile(os.path.join(CONFIG['HOME'], file)):
			if file.rsplit('.', 1)[1] in ['mp4', 'flv', 'avi', 'mkv', 'm4v']:
					try:
						parse_filename(file)
					except RenamrException as err:
						print('{}: {}'.format(file, err))


main()
