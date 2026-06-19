def test_run_importable():
	import run
	assert callable(run.main)
