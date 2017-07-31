import re
import os
import shutil
import requests
import json

config = {}
token = None

SERIES_PARSER = [
	re.compile("^(?P<show>.*?)s *(?P<season>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
	re.compile("^(?P<show>.*?)(?P<season>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
	re.compile("^(?P<show>(?:.*?\D|))(?P<season>\d{1,2})(?P<episode>\d{2})(?:\D.*|)\.(?P<extension>.*?)$", re.IGNORECASE),
	]
ACCEPTED_EXTENSIONS = ['mp4', 'flv', 'avi', 'mkv']

def parse_filename(filename):
	for parser in SERIES_PARSER:
		matches = parser.search(filename)
		try:
			match_dict = matches.groupdict()
			break
		except AttributeError:
			continue
	else:
		raise Exception('Filename %s not matched.' % (filename,))

	show = match_dict['show'].replace('.', ' ').strip()
	season = str(int(match_dict['season']))
	episode = str(int(match_dict['episode']))
	extension = match_dict['extension']

	seriesid, show = get_seriesid(show)
	if seriesid is None or show is None:
		raise Exception('Ignoring %s' % (filename,))
	episodename = get_episode(seriesid, season, episode)
	if episodename is None:
		raise Exception('Couldn\'t find %s S%sE%s.' % (show,season,episode,))

	rename = check_with_user(filename, season, episode, episodename, extension)
	if rename:
		rename_and_move(filename, rename, show, season)

def login():
	data = { 'apikey':config['TVDB_KEY'], 'userkey':config['TVDB_USER'], 'username':config['TVDB_NAME'] }
	headers = { 'content-type':'application/json' }
	r = requests.post('https://api.thetvdb.com/login', data=json.dumps(data), headers=headers).text
	resp = json.loads(r)
	if 'Error' in resp:
		raise Exception(resp['Error'])
	return resp['token']

def get_seriesid(show):
	params = { 'name':show }
	headers = { 'content-type':'application/json', 'Authorization':'Bearer %s' % config['TVDB_TOKEN'] }
	r = requests.get('https://api.thetvdb.com/search/series', params=params, headers=headers).text
	resp = json.loads(r)

	if 'Error' in resp:
		raise Exception(resp['Error'])

	found = resp['data']

	if len(found) == 0:
		raise Exception('No series matches for %s' % (show,))
	elif len(found) == 1:
		return found[0]['id'], found[0]['seriesName']
	else:
		for i in range(0, len(found)):
			print('(%s) %s' % (i+1, found[i]['seriesName']))
		choice = input('Select correct series for %s ("i" to ignore): ' % (show,)).strip()
		if choice == '':
			return found[0]['id'], found[0]['seriesName']
		elif choice == 'i':
			return None, None
		elif int(choice) < 1 or int(choice) > len(found):
			raise Exception('Invalid input.')
		else:
			return found[int(choice)-1]['id'], found[int(choice)-1]['seriesName']
			
def get_episode(seriesid, season, episode):
	params = { 'airedSeason':season, 'airedEpisode':episode }
	headers = { 'content-type':'application/json', 'Authorization':'Bearer %s' % config['TVDB_TOKEN'] }
	r = requests.get('https://api.thetvdb.com/series/%s/episodes/query' % seriesid, params=params, headers=headers).text
	resp = json.loads(r)

	if 'Error' in resp:
		raise Exception(resp['Error'])

	found = resp['data']

	episode_name = None

	for e in found:
		if int(e['airedSeason']) == int(season) and int(e['airedEpisodeNumber']) == int(episode):
			episode_name = e['episodeName']

	return episode_name

def check_with_user(filename, season, episode, episodename, extension):
	if int(season) < 10:
		season = '0' + season
	if int(episode) < 10:
		episode = '0' + episode
	new_filename = 'S%sE%s - %s.%s' % (season, episode, episodename, extension)
	print('Current: %s' % (filename,))
	print('New: %s' % (new_filename,))
	choice = input('Confirm change? ("n" for no, "i" to ignore): ').strip()
	if choice.lower() == 'i' or choice.lower() == 'n':
		raise Exception('Ignoring %s' % (filename,))
	return winsafe_filename(new_filename)

def rename_and_move(filename, new_filename, show, season):
	show_folder = os.path.join(config['MOVED'], show)
	if not os.path.exists(show_folder):
		os.makedirs(show_folder)
	season_folder = os.path.join(show_folder, 'Season %s' % (season,))
	if not os.path.exists(season_folder):
		os.makedirs(season_folder)
	curr_file = os.path.join(config['HOME'], filename)
	new_file = os.path.join(season_folder, new_filename)
	if os.path.exists(new_file):
		raise Exception('%s already Exists.' % (new_file,))
	shutil.move(curr_file, new_file)
	print('Successfully moved.')

def winsafe_filename(filename):
	return re.sub(r'[\\/:"*?<>|]+', "", filename)

def main():
	print('Running renamr...')
	with open('config.cfg') as f:
		content = f.readlines()
	for line in content:
		(key, value) = line.replace('\n','').split(' = ')
		config[key] = value

	config['TVDB_TOKEN'] = login()

	print('Checking for files in %s' % config['HOME'])
	for f in os.listdir(config['HOME']):
		if os.path.isfile(os.path.join(config['HOME'],f)) and f.rsplit('.',1)[1] in ACCEPTED_EXTENSIONS:
			try:
				parse_filename(f)
			except Exception as e:
				print(e)

main()