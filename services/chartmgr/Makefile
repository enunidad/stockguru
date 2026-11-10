PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install smoke run test clean

smoke:
	@set -e; \
	$(PYTHON) -m src.main & server=$$!; \
	trap 'kill "$$server" 2>/dev/null || true; wait "$$server" 2>/dev/null || true' EXIT; \
	sleep 2; \
	$(PYTHON) -c "import json, urllib.request; response = urllib.request.urlopen('http://localhost:8050/health', timeout=5); raise SystemExit(json.load(response).get('status') != 'ok')"; \
	echo "Chartmgr smoke test passed"

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m src.main

test:
	$(PYTHON) -m pytest tests -v

clean:
	@$(PYTHON) -c "import shutil, pathlib; \
		root = pathlib.Path('.'); \
		dirs = ['__pycache__', '.pytest_cache', 'htmlcov', 'build', 'dist']; \
		[shutil.rmtree(p, ignore_errors=True) for d in dirs for p in root.rglob(d)]; \
		[p.unlink() for ext in ('*.pyc', '*.pyo', '.coverage') for p in root.rglob(ext)]"
