import json

import pytest

import history


class TestLoadHistory:
	def test_missing_file_returns_empty(self, isolate_rename_history):
		data = history.load_history()
		assert data == {'version': 1, 'batches': []}
		assert not isolate_rename_history.exists()

	def test_loads_existing_file(self, isolate_rename_history):
		payload = {
			'version': 1,
			'batches': [
				{
					'id': 'batch-1',
					'moves': [{'src': '/a', 'dest': '/b'}],
				}
			],
		}
		isolate_rename_history.write_text(json.dumps(payload))
		assert history.load_history() == payload

	def test_invalid_json_raises(self, isolate_rename_history):
		isolate_rename_history.write_text('not-json')
		with pytest.raises(history.HistoryException, match='Failed to read'):
			history.load_history()

	def test_invalid_format_raises(self, isolate_rename_history):
		isolate_rename_history.write_text(
			json.dumps({'version': 1, 'batches': 'nope'})
		)
		with pytest.raises(history.HistoryException, match='Invalid'):
			history.load_history()


class TestSaveAndAppend:
	def test_append_batch_writes_moves(self, isolate_rename_history):
		moves = [{'src': '/home/a.mp4', 'dest': '/moved/a.mp4'}]
		history.append_batch(moves)

		data = history.load_history()
		assert len(data['batches']) == 1
		assert data['batches'][0]['moves'] == moves
		assert 'id' in data['batches'][0]
		assert isolate_rename_history.exists()

	def test_append_empty_batch_is_noop(self, isolate_rename_history):
		history.append_batch([])
		assert not isolate_rename_history.exists()

	def test_append_trims_to_max_batches(
		self, isolate_rename_history, monkeypatch
	):
		monkeypatch.setattr(history, 'MAX_BATCHES', 3)
		for i in range(5):
			history.append_batch([{'src': f'/s{i}', 'dest': f'/d{i}'}])

		data = history.load_history()
		assert len(data['batches']) == 3
		assert data['batches'][0]['moves'][0]['src'] == '/s2'
		assert data['batches'][-1]['moves'][0]['src'] == '/s4'

	def test_save_is_atomic_replace(self, isolate_rename_history):
		history.save_history({
			'version': 1,
			'batches': [{'id': 'x', 'moves': []}],
		})
		assert isolate_rename_history.exists()
		leftovers = list(
			isolate_rename_history.parent.glob('.rename_history_*')
		)
		assert leftovers == []

	def test_save_replace_failure_raises(self, isolate_rename_history, monkeypatch):
		def fail_replace(src, dst):
			raise OSError('disk full')

		monkeypatch.setattr(history.os, 'replace', fail_replace)

		with pytest.raises(history.HistoryException, match='Failed to write'):
			history.save_history({'version': 1, 'batches': []})

		leftovers = list(
			isolate_rename_history.parent.glob('.rename_history_*')
		)
		assert leftovers == []

	def test_save_cleanup_ignores_unlink_errors(
		self, isolate_rename_history, monkeypatch
	):
		def fail_replace(src, dst):
			raise OSError('disk full')

		def fail_unlink(path):
			raise OSError('busy')

		monkeypatch.setattr(history.os, 'replace', fail_replace)
		monkeypatch.setattr(history.os, 'unlink', fail_unlink)

		with pytest.raises(history.HistoryException, match='Failed to write'):
			history.save_history({'version': 1, 'batches': []})
