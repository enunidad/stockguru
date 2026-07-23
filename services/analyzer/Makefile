PYTHON ?= python

smoke:
	powershell -NoProfile -Command \
		"$$server = Start-Process python \
			-ArgumentList '-m src.main' \
			-PassThru; \
		Start-Sleep -Seconds 2; \
		try { \
			$$response = Invoke-RestMethod \
				'http://localhost:8090/health'; \
			if ($$response.status -ne 'ok') { \
				throw 'Analyzer health check failed' \
			}; \
			Write-Host 'Analyzer smoke test passed' \
		} finally { \
			if (Get-Process -Id $$server.Id \
				-ErrorAction SilentlyContinue) { \
				Stop-Process -Id $$server.Id \
			} \
		}"

run:
	$(PYTHON) -m src.main

clean:
	$(PYTHON) -c "import shutil, pathlib; \
		root = pathlib.Path('.'); \
		dirs = ['__pycache__', '.pytest_cache', 'htmlcov', 'build', 'dist']; \
		[shutil.rmtree(p, ignore_errors=True) for d in dirs for p in root.rglob(d)]; \
		[p.unlink() for ext in ('*.pyc', '*.pyo', '.coverage') for p in root.rglob(ext)]"