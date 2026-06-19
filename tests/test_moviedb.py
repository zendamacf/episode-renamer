from unittest.mock import patch

import pytest

import moviedb


class TestStripYear:
	def test_removes_parenthetical_year(self):
		assert moviedb._strip_year('The Office (2005)') == 'The Office'

	def test_leaves_name_without_year(self):
		assert moviedb._strip_year('Breaking Bad') == 'Breaking Bad'


class TestExtractYear:
	def test_extracts_year_from_iso_date(self):
		assert moviedb._extract_year('2005-03-24') == 2005

	def test_empty_string_returns_none(self):
		assert moviedb._extract_year('') is None

	def test_none_returns_none(self):
		assert moviedb._extract_year(None) is None


class TestRequest:
	@patch('moviedb.requests.get')
	def test_get_success_returns_json(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(200, {'ok': True})

		result = moviedb._request('/search/tv', 'GET', params={'api_key': 'key'})

		assert result == {'ok': True}
		mock_get.assert_called_once_with(
			'https://api.themoviedb.org/3/search/tv',
			params={'api_key': 'key'},
			data=None,
			headers={
				'Content-Type': 'application/json',
				'Accept': 'application/json',
			},
		)

	@patch('moviedb.requests.post')
	def test_post_uses_post_method(self, mock_post, mock_http_response):
		mock_post.return_value = mock_http_response(200, {'ok': True})

		result = moviedb._request('/token', 'POST', data='{}')

		assert result == {'ok': True}
		mock_post.assert_called_once()

	@patch('moviedb.requests.get')
	def test_not_found_returns_empty_dict(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(404)

		assert moviedb._request('/missing', 'GET') == {}

	@patch('moviedb.requests.get')
	def test_server_error_raises(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(500, text='Internal Server Error')

		with pytest.raises(moviedb.MovieDBException, match='Unexpected response'):
			moviedb._request('/search/tv', 'GET')


class TestGetSeries:
	@patch('moviedb._request')
	def test_parses_search_results(self, mock_request, tmdb_search_response):
		mock_request.return_value = tmdb_search_response

		results = moviedb.get_series('The Office', 'test-key')

		assert len(results) == 2
		assert results[0] == {'id': 2316, 'name': 'The Office', 'year': 2005}
		assert results[1] == {'id': 9999, 'name': 'The Office', 'year': 2010}
		mock_request.assert_called_once_with(
			'/search/tv',
			'GET',
			params={'api_key': 'test-key', 'query': 'The Office'},
		)

	@patch('moviedb._request')
	def test_skips_results_missing_airdate(self, mock_request, capsys):
		mock_request.return_value = {
			'results': [{'id': 1, 'name': 'No Date Show'}],
		}

		results = moviedb.get_series('No Date Show', 'test-key')

		assert results == []
		assert 'Ignoring missing airdate No Date Show.' in capsys.readouterr().out

	@patch('moviedb._request')
	def test_empty_results(self, mock_request):
		mock_request.return_value = {'results': []}

		assert moviedb.get_series('Unknown', 'test-key') == []

	@patch('moviedb._request')
	def test_not_found_returns_empty_list(self, mock_request):
		mock_request.return_value = {}

		assert moviedb.get_series('Unknown', 'test-key') == []


class TestGetEpisode:
	@patch('moviedb._request')
	def test_returns_episode_name(self, mock_request, tmdb_episode_response):
		mock_request.return_value = tmdb_episode_response

		name = moviedb.get_episode(2316, 1, 1, 'test-key')

		assert name == 'Pilot'
		mock_request.assert_called_once_with(
			'/tv/2316/season/1/episode/1',
			'GET',
			params={'api_key': 'test-key'},
		)

	@patch('moviedb._request')
	def test_not_found_returns_none(self, mock_request):
		mock_request.return_value = {}

		assert moviedb.get_episode(2316, 99, 99, 'test-key') is None
