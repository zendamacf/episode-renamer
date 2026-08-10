from unittest.mock import Mock, patch

import pytest
import requests
from helpers import assert_logged

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

	def test_invalid_date_returns_none(self):
		assert moviedb._extract_year('not-a-date') is None


class TestRetryDelay:
	def test_uses_retry_after_header(self):
		response = Mock()
		response.headers = {'Retry-After': '1.5'}
		assert moviedb._retry_delay(response, 0) == 1.5

	def test_falls_back_to_exponential_backoff(self):
		assert moviedb._retry_delay(None, 2) == 4.0

	def test_invalid_retry_after_uses_backoff(self):
		response = Mock()
		response.headers = {'Retry-After': 'soon'}
		assert moviedb._retry_delay(response, 1) == 2.0


class TestRequest:
	@patch('moviedb.requests.get')
	def test_get_success_returns_json(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(200, {'ok': True})

		result = moviedb._request('/search/tv', params={'api_key': 'key'})

		assert result == {'ok': True}
		mock_get.assert_called_once_with(
			'https://api.themoviedb.org/3/search/tv',
			params={'api_key': 'key'},
			headers={
				'Content-Type': 'application/json',
				'Accept': 'application/json',
			},
			timeout=moviedb.DEFAULT_TIMEOUT,
		)

	@patch('moviedb.requests.get')
	def test_not_found_returns_empty_dict(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(404)

		assert moviedb._request('/missing') == {}

	@patch('moviedb.time.sleep')
	@patch('moviedb.requests.get')
	def test_server_error_raises_after_retries(self, mock_get, mock_sleep, mock_http_response):
		mock_get.return_value = mock_http_response(500, text='Internal Server Error')

		with pytest.raises(moviedb.MovieDBException, match='Unexpected response'):
			moviedb._request('/search/tv')

		assert mock_get.call_count == moviedb.MAX_RETRIES
		assert mock_sleep.call_count == moviedb.MAX_RETRIES - 1

	@patch('moviedb.time.sleep')
	@patch('moviedb.requests.get')
	def test_retries_on_connection_error_then_succeeds(
		self, mock_get, mock_sleep, mock_http_response
	):
		mock_get.side_effect = [
			requests.ConnectionError('boom'),
			mock_http_response(200, {'ok': True}),
		]

		assert moviedb._request('/search/tv') == {'ok': True}
		assert mock_get.call_count == 2
		mock_sleep.assert_called_once()

	@patch('moviedb.time.sleep')
	@patch('moviedb.requests.get')
	def test_retries_on_429_then_succeeds(self, mock_get, mock_sleep, mock_http_response):
		rate_limited = mock_http_response(429, text='Slow down')
		rate_limited.headers = {'Retry-After': '0'}
		mock_get.side_effect = [
			rate_limited,
			mock_http_response(200, {'ok': True}),
		]

		assert moviedb._request('/search/tv') == {'ok': True}
		mock_sleep.assert_called_once_with(0.0)

	@patch('moviedb.time.sleep')
	@patch('moviedb.requests.get')
	def test_connection_errors_exhaust_retries(self, mock_get, mock_sleep):
		mock_get.side_effect = requests.ConnectionError('down')

		with pytest.raises(moviedb.MovieDBException, match='failed after'):
			moviedb._request('/search/tv')

		assert mock_get.call_count == moviedb.MAX_RETRIES

	@patch('moviedb.requests.get')
	def test_invalid_json_raises(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(200, text='{not-json')

		with pytest.raises(moviedb.MovieDBException, match='Invalid JSON'):
			moviedb._request('/search/tv')

	@patch('moviedb.requests.get')
	def test_client_error_raises_without_retry(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(401, text='Unauthorized')

		with pytest.raises(moviedb.MovieDBException, match='Unexpected response'):
			moviedb._request('/search/tv')

		mock_get.assert_called_once()


class TestGetSeries:
	@patch('moviedb._request')
	def test_parses_search_results(self, mock_request, tmdb_search_response):
		mock_request.return_value = tmdb_search_response

		results = moviedb.get_series('The Office', 'test-key')

		assert len(results) == 2
		assert results[0] == {
			'id': 2316,
			'name': 'The Office',
			'year': 2005,
			'country': ['US'],
		}
		assert results[1] == {
			'id': 9999,
			'name': 'The Office',
			'year': 2001,
			'country': ['GB'],
		}
		mock_request.assert_called_once_with(
			'/search/tv',
			params={'api_key': 'test-key', 'query': 'The Office'},
		)

	@patch('moviedb._request')
	def test_skips_results_missing_airdate(self, mock_request, capsys):
		mock_request.return_value = {
			'results': [{'id': 1, 'name': 'No Date Show'}],
		}

		results = moviedb.get_series('No Date Show', 'test-key')

		assert results == []
		assert_logged(capsys.readouterr().out, ('Ignoring', 'No Date Show'))

	@patch('moviedb._request')
	def test_empty_results(self, mock_request):
		mock_request.return_value = {'results': []}

		assert moviedb.get_series('Unknown', 'test-key') == []

	@patch('moviedb._request')
	def test_not_found_returns_empty_list(self, mock_request):
		mock_request.return_value = {}

		assert moviedb.get_series('Unknown', 'test-key') == []

	@patch('moviedb._request')
	def test_invalid_airdate_yields_none_year(self, mock_request):
		mock_request.return_value = {
			'results': [
				{
					'id': 1,
					'name': 'Odd Show',
					'first_air_date': 'yesterday',
				}
			],
		}

		results = moviedb.get_series('Odd Show', 'test-key')

		assert results == [{'id': 1, 'name': 'Odd Show', 'year': None, 'country': None}]

	@patch('moviedb._request')
	def test_missing_origin_country_yields_none(self, mock_request):
		mock_request.return_value = {
			'results': [
				{
					'id': 1,
					'name': 'Survivor',
					'first_air_date': '2000-05-31',
				}
			],
		}

		results = moviedb.get_series('Survivor', 'test-key')

		assert results == [{'id': 1, 'name': 'Survivor', 'year': 2000, 'country': None}]

	@patch('moviedb._request')
	def test_empty_origin_country_yields_none(self, mock_request):
		mock_request.return_value = {
			'results': [
				{
					'id': 1,
					'name': 'Survivor',
					'first_air_date': '2000-05-31',
					'origin_country': [],
				}
			],
		}

		results = moviedb.get_series('Survivor', 'test-key')

		assert results == [{'id': 1, 'name': 'Survivor', 'year': 2000, 'country': None}]

	@patch('moviedb._request')
	def test_multiple_origin_countries_are_preserved(self, mock_request):
		mock_request.return_value = {
			'results': [
				{
					'id': 1,
					'name': 'International Show',
					'first_air_date': '2020-01-01',
					'origin_country': ['US', 'CA'],
				}
			],
		}

		results = moviedb.get_series('International Show', 'test-key')

		assert results == [
			{
				'id': 1,
				'name': 'International Show',
				'year': 2020,
				'country': ['US', 'CA'],
			}
		]


class TestGetEpisode:
	@patch('moviedb._request')
	def test_returns_episode_name(self, mock_request, tmdb_episode_response):
		mock_request.return_value = tmdb_episode_response

		name = moviedb.get_episode(2316, 1, 1, 'test-key')

		assert name == 'Pilot'
		mock_request.assert_called_once_with(
			'/tv/2316/season/1/episode/1',
			params={'api_key': 'test-key'},
		)

	@patch('moviedb._request')
	def test_not_found_returns_none(self, mock_request):
		mock_request.return_value = {}

		assert moviedb.get_episode(2316, 99, 99, 'test-key') is None

	@patch('moviedb._request')
	def test_missing_name_returns_none(self, mock_request):
		mock_request.return_value = {'id': 1}

		assert moviedb.get_episode(2316, 1, 1, 'test-key') is None
