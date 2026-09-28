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

		with pytest.raises(moviedb.MovieDBException, match='TMDB server error'):
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
		secret = 'super-secret-api-key'
		mock_get.return_value = mock_http_response(
			401,
			text=f'Invalid API key: {secret}',
		)

		with pytest.raises(
			moviedb.MovieDBException, match='authentication failed \\(401\\)'
		) as exc:
			moviedb._request('/search/tv', params={'api_key': secret})

		mock_get.assert_called_once()
		assert secret not in str(exc.value)

	@patch('moviedb.requests.get')
	def test_bad_request_error_is_sanitized(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(400, text='{"errors":["bad"]}')

		with pytest.raises(moviedb.MovieDBException, match='rejected the request'):
			moviedb._request('/search/tv')

	@patch('moviedb.requests.get')
	def test_unknown_client_error_is_generic(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(418, text='teapot')

		with pytest.raises(moviedb.MovieDBException, match='request failed \\(418\\)'):
			moviedb._request('/search/tv')

	@patch('moviedb.requests.get')
	def test_forbidden_error_is_sanitized(self, mock_get, mock_http_response):
		mock_get.return_value = mock_http_response(403, text='{"status_code":403,"body":"secret"}')

		with pytest.raises(
			moviedb.MovieDBException, match='authentication failed \\(403\\)'
		) as exc:
			moviedb._request('/search/tv')

		mock_get.assert_called_once()
		assert 'secret' not in str(exc.value)


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
			params={'api_key': 'test-key', 'query': 'The Office', 'page': '1'},
		)

	@patch('moviedb._request')
	def test_search_series_page_requests_specific_page(self, mock_request):
		mock_request.return_value = {
			'results': [],
			'total_pages': 5,
			'page': 2,
		}

		data = moviedb.search_series_page('Show', 'test-key', page=2)

		assert data['page'] == 2
		assert data['total_pages'] == 5
		mock_request.assert_called_once_with(
			'/search/tv',
			params={'api_key': 'test-key', 'query': 'Show', 'page': '2'},
		)

	@patch('moviedb.search_series_page')
	def test_fetch_next_page_merges_and_dedupes(self, mock_search_page):
		mock_search_page.side_effect = [
			{
				'results': [{'id': 1, 'name': 'A', 'year': 2000, 'country': None}],
				'page': 1,
				'total_pages': 2,
			},
			{
				'results': [
					{'id': 1, 'name': 'A', 'year': 2000, 'country': None},
					{'id': 2, 'name': 'B', 'year': 2001, 'country': None},
				],
				'page': 2,
				'total_pages': 2,
			},
		]
		session = moviedb.begin_series_search('Show', 'key')
		assert len(session.results) == 1
		assert moviedb.fetch_next_page(session) is True
		assert [s['id'] for s in session.results] == [1, 2]

	@patch('moviedb.search_series_page')
	def test_find_series_in_search_loads_until_id_found(self, mock_search_page):
		mock_search_page.side_effect = [
			{
				'results': [{'id': 1, 'name': 'A', 'year': 2000, 'country': None}],
				'page': 1,
				'total_pages': 2,
			},
			{
				'results': [{'id': 2, 'name': 'B', 'year': 2001, 'country': None}],
				'page': 2,
				'total_pages': 2,
			},
		]
		found = moviedb.find_series_in_search('Show', 'key', 2)
		assert found is not None
		assert found['id'] == 2
		assert mock_search_page.call_count == 2

	@patch('moviedb.search_series_page')
	def test_fetch_next_page_warns_when_capped(self, mock_search_page, capsys):
		mock_search_page.side_effect = [
			{
				'results': [{'id': 1, 'name': 'A', 'year': 2000, 'country': None}],
				'page': 1,
				'total_pages': 5,
			},
			{
				'results': [{'id': 2, 'name': 'B', 'year': 2001, 'country': None}],
				'page': 2,
				'total_pages': 5,
			},
			{
				'results': [{'id': 3, 'name': 'C', 'year': 2002, 'country': None}],
				'page': 3,
				'total_pages': 5,
			},
		]
		session = moviedb.begin_series_search('Show', 'key')
		assert moviedb.fetch_next_page(session) is True
		assert moviedb.fetch_next_page(session) is True
		assert moviedb.fetch_next_page(session) is False
		assert_logged(capsys.readouterr().out, ('TMDB', 'top 3 result pages only'))

	@patch('moviedb.search_series_page')
	def test_find_series_in_search_returns_none_when_missing(self, mock_search_page):
		mock_search_page.return_value = {
			'results': [{'id': 1, 'name': 'A', 'year': 2000, 'country': None}],
			'page': 1,
			'total_pages': 1,
		}
		assert moviedb.find_series_in_search('Show', 'key', 99) is None

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
