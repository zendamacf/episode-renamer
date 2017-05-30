import re
import os
import shutil
import requests
import urllib.request
import xml.etree.ElementTree as ET

TVDB = 'http://www.thetvdb.com/api/'
config = {}

SERIES_PARSER = [
	re.compile("^(?P<show>.*?)s *(?P<season>\d+) *e *(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
	re.compile("^(?P<show>.*?)(?P<season>\d+)x(?P<episode>\d+).*\.(?P<extension>.*?)$", re.IGNORECASE),
	re.compile("^(?P<show>(?:.*?\D|))(?P<season>\d{1,2})(?P<episode>\d{2})(?:\D.*|)\.(?P<extension>.*?)$", re.IGNORECASE),
	]
ACCEPTED_EXTENSIONS = ['mp4', 'flv', 'avi', 'mkv']

class RenamrException(Exception):
	pass

def parse_filename(filename):
	for parser in SERIES_PARSER:
		matches = parser.search(filename)
		try:
			match_dict = matches.groupdict()
			break
		except AttributeError:
			continue
	else:
		raise RenamrException('Filename %s not matched.' % (filename,))

	show = match_dict['show'].replace('.', ' ').strip()
	season = str(int(match_dict['season']))
	episode = str(int(match_dict['episode']))
	extension = match_dict['extension']

	seriesid, show = get_seriesid(show)
	if seriesid is None or show is None:
		raise RenamrException('Ignoring %s' % (filename,))
	episodename = get_episode(seriesid, season, episode)
	if episodename is None:
		raise RenamrException('Couldn\'t find %s S%sE%s.' % (show,season,episode,))

	rename = check_with_user(filename, season, episode, episodename, extension)
	if rename:
		rename_and_move(filename, rename, show, season)

def get_seriesid(show):
	params = {'seriesname':show}
	r = requests.get(TVDB+'GetSeries.php', params=params).text
	print(r)
	root = ET.fromstring(r)
	found = []
	for child in root.findall('Series'):
		found.append({ 'seriesid':child.find('seriesid').text, 
			'seriesname':child.find('SeriesName').text.encode('utf-8').decode('unicode_escape').encode('ascii','ignore').decode() })
	if len(found) == 0:
		raise RenamrException('No series matches for %s' % (show,))
	elif len(found) == 1:
		return found[0]['seriesid'], found[0]['seriesname']
	else:
		for i in range(0, len(found)):
			print('(%s) %s' % (i+1, found[i]['seriesname']))
		choice = input('Select correct series for %s ("i" to ignore): ' % (show,)).strip()
		if choice == '':
			return found[0]['seriesid'], found[0]['seriesname']
		elif choice == 'i':
			return None, None
		elif int(choice) < 1 or int(choice) > len(found):
			raise RenamrException('Invalid input.')
		else:
			return found[int(choice)-1]['seriesid'], found[int(choice)-1]['seriesname']

def get_episode(seriesid, season, episode):
	params = {'apikey':config['TVDB_KEY'], 'seriesid':seriesid}
	r = urllib.request.urlopen(TVDB+'%s/series/%s/all/en.xml' % (config['TVDB_KEY'], seriesid,)).read()
	root = ET.fromstring(r)
	for child in root.findall('Episode'):
		if child.find('SeasonNumber').text == season and child.find('EpisodeNumber').text == episode:
			return child.find('EpisodeName').text.encode('utf-8').decode('unicode_escape').encode('ascii','ignore').decode()
	return None

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
		raise RenamrException('Ignoring %s' % (filename,))
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
		raise RenamrException('%s already Exists.' % (new_file,))
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

	print('Checking for files in %s' % config['HOME'])
	for f in os.listdir(config['HOME']):
		if os.path.isfile(os.path.join(config['HOME'],f)) and f.rsplit('.',1)[1] in ACCEPTED_EXTENSIONS:
			try:
				parse_filename(f)
			except RenamrException as e:
				print(e)

main()