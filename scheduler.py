import os
import datetime
import shutil
import requests
import urllib.request
import xml.etree.ElementTree as ET

TVDB = 'http://www.thetvdb.com/api/'
config = {}

def get_seriesid(show):
	params = {'seriesname':show}
	r = requests.get(TVDB+'GetSeries.php', params=params).text
	root = ET.fromstring(r)
	found = []
	for child in root.findall('Series'):
		found.append({ 'seriesid':child.find('seriesid').text, 
			'seriesname':child.find('SeriesName').text.encode('utf-8').decode('unicode_escape').encode('ascii','ignore').decode() })
	if len(found) == 0:
		raise RenamrException('No series matches for %s' % (show,))
	else:
		return found[0]['seriesid']

def get_episodeinfo(seriesid, airdate):
	info = ''
	if seriesid is not None:
		params = { 'apikey':config['TVDB_KEY'], 'seriesid':seriesid, 'airdate':airdate }
		r = requests.get(TVDB+'GetEpisodeByAirDate.php', params=params).text
		if 'EpisodeNumber' in r:
			root = ET.fromstring(r)
			for child in root.findall('Episode'):
				season = child.find('SeasonNumber').text
				episode = child.find('EpisodeNumber').text
				if int(season) < 10:
					season = '0' + season
				if int(episode) < 10:
					episode = '0' + episode
				info = ' S%sE%s' % (season, episode,)
	return info

def main():
	with open('config.cfg') as f:
		content = f.readlines()
	for line in content:
		(key, value) = line.replace('\n','').split(' = ')
		config[key] = value

	now = datetime.datetime.today()
	numdays = 21
	datelist = []
	for x in range (0, numdays):
		datelist.append(now + datetime.timedelta(days=x))

	for d in datelist:
		folder = os.path.join(config['SCHED_LOC'], d.strftime('%Y-%m-%d %A'))
		if not os.path.exists(folder):
			# Make day folders
			os.makedirs(folder)
		if len(os.listdir(folder)) == 0:
			for fol in os.listdir(config['CURR_LOC']):
				if d.strftime('%A').lower() in fol.lower():
					curr = os.path.join(config['CURR_LOC'], fol)
					for fil in os.listdir(curr):
						seriesid = get_seriesid(fil.rsplit('.',1)[0])
						info = get_episodeinfo(seriesid, (d-datetime.timedelta(days=1)).strftime('%Y-%m-%d'))
						fil_split = fil.rsplit('.', 1)
						newname = fil_split[0] + info + '.' + fil_split[1]
						print(newname)
						shutil.copy(os.path.join(curr, fil), folder)
						os.rename(os.path.join(folder,fil), os.path.join(folder,newname))
		if len(os.listdir(folder)) == 0:
			os.rmdir(folder)

main()